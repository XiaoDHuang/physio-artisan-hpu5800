"""PostgreSQL 会话历史存储实现。

把对话历史持久化到 hpu_db 的 chat_conversations 表（按 conversation_id）。
- 表结构在首次使用时自动创建（幂等），不依赖外部建表脚本。
- 不复用现有的 ai_conversations 表：后者要求 user_id NOT NULL 且外键关联 users，
  不适合本接口的匿名 / 无登录会话。本表独立、自包含。

阻塞式 psycopg2 调用通过 asyncio.to_thread 放到线程池执行，避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List

from psycopg2.extras import Json

from .conversation_store import (
    ConversationStore,
    ConversationSummary,
    DEFAULT_MAX_TURNS,
)
from .db import get_pool


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chat_conversations (
    conversation_id VARCHAR(64) PRIMARY KEY,
    messages        JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class PostgresConversationStore(ConversationStore):
    """基于 PostgreSQL 的会话历史存储。

    Args:
        max_turns: 每个会话保留的最大轮数（1 轮 = user + assistant），超出裁剪最早记录。
    """

    def __init__(self, max_turns: int = DEFAULT_MAX_TURNS) -> None:
        self._max_messages = max(1, max_turns) * 2
        self._initialized = False
        self._init_lock = asyncio.Lock()

    # --------------------- 连接 / 建表 ---------------------
    def _run(self, fn):
        """从连接池借一个连接执行 fn(conn)，自动提交 / 回滚 / 归还。"""
        pool = get_pool()
        conn = pool.getconn()
        try:
            result = fn(conn)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)

    async def _ensure_table(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return

            def create(conn):
                with conn.cursor() as cur:
                    cur.execute(_CREATE_TABLE_SQL)

            await asyncio.to_thread(self._run, create)
            self._initialized = True

    # --------------------- 接口实现 ---------------------
    async def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        await self._ensure_table()

        def query(conn):
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT messages FROM chat_conversations WHERE conversation_id = %s",
                    (conversation_id,),
                )
                row = cur.fetchone()
                return row[0] if row else []

        messages = await asyncio.to_thread(self._run, query)
        # JSONB 列已是 list；兜底处理字符串情况
        if isinstance(messages, str):
            messages = json.loads(messages)
        return messages or []

    async def append(self, conversation_id: str, messages: List[Dict[str, str]]) -> None:
        if not messages:
            return
        await self._ensure_table()
        limit = self._max_messages

        def upsert(conn):
            with conn.cursor() as cur:
                # 追加并用滑动窗口裁剪：拼接后只保留最后 limit 条
                cur.execute(
                    """
                    INSERT INTO chat_conversations (conversation_id, messages, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (conversation_id) DO UPDATE SET
                        messages = (
                            SELECT to_jsonb(array_agg(m))
                            FROM (
                                SELECT m
                                FROM jsonb_array_elements(
                                    chat_conversations.messages || EXCLUDED.messages
                                ) WITH ORDINALITY AS t(m, ord)
                                ORDER BY ord
                                OFFSET GREATEST(
                                    jsonb_array_length(
                                        chat_conversations.messages || EXCLUDED.messages
                                    ) - %s, 0
                                )
                            ) sub
                        ),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (conversation_id, Json(messages), limit),
                )

        await asyncio.to_thread(self._run, upsert)

    async def clear(self, conversation_id: str) -> None:
        await self._ensure_table()

        def delete(conn):
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM chat_conversations WHERE conversation_id = %s",
                    (conversation_id,),
                )

        await asyncio.to_thread(self._run, delete)

    async def list_conversations(self) -> List[ConversationSummary]:
        await self._ensure_table()

        def query(conn):
            with conn.cursor() as cur:
                # 直接在 SQL 里取首条 user 消息作标题，避免回传全部 messages
                cur.execute(
                    """
                    SELECT
                        conversation_id,
                        COALESCE((
                            SELECT m ->> 'content'
                            FROM jsonb_array_elements(messages) AS m
                            WHERE m ->> 'role' = 'user'
                            LIMIT 1
                        ), '') AS title,
                        EXTRACT(EPOCH FROM updated_at) AS updated_at
                    FROM chat_conversations
                    WHERE jsonb_array_length(messages) > 0
                    ORDER BY updated_at DESC
                    """
                )
                return cur.fetchall()

        rows = await asyncio.to_thread(self._run, query)
        result: List[ConversationSummary] = []
        for cid, title, updated_at in rows:
            clean = (title or "").strip().replace("\n", " ")[:30] or "新对话"
            result.append({
                "conversation_id": cid,
                "title": clean,
                "updated_at": float(updated_at or 0.0),
            })
        return result
