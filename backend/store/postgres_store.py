"""PostgreSQL 会话历史存储实现（统一到 ai_conversations 表）。

设计变更（统一持久化）：
- 原先独立的 chat_conversations 表已废弃，会话历史统一收敛到项目既有的
  ai_conversations 表，按 session_id 维护（一会话一行，UPSERT 滑窗裁剪）。
- 暂无用户态：所有会话归属到 seed_xiaoming.sql 插入的演示用户（小明 id=1）。
- 同一行还可回写一次健康决策的产出（training_plan / meal_plan / agent_decisions /
  safety_logs / recommendations / speech_report），实现"对话 + 报告"同源存档。

阻塞式 psycopg2 调用通过 asyncio.to_thread 放到线程池执行，避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Any

from psycopg2.extras import Json, RealDictCursor

from .conversation_store import (
    ConversationStore,
    ConversationSummary,
    DEFAULT_MAX_TURNS,
)
from .db import get_pool

# 暂无用户态：统一归属到演示用户（与 intake.DEFAULT_USER_ID 保持一致）
DEFAULT_USER_ID = 1

# 保证 session_id 可作为 UPSERT 冲突键（幂等）
_ENSURE_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_conv_session ON ai_conversations(session_id)"
)


class PostgresConversationStore(ConversationStore):
    """基于 PostgreSQL ai_conversations 表的会话历史存储。

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

            def ensure(conn):
                with conn.cursor() as cur:
                    # ai_conversations 表由 hpu_db.sql 建好；此处仅补会话唯一索引
                    cur.execute(_ENSURE_INDEX_SQL)

            await asyncio.to_thread(self._run, ensure)
            self._initialized = True

    # --------------------- 接口实现 ---------------------
    async def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        await self._ensure_table()

        def query(conn):
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT messages FROM ai_conversations WHERE session_id = %s",
                    (conversation_id,),
                )
                row = cur.fetchone()
                return row[0] if row else []

        messages = await asyncio.to_thread(self._run, query)
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
                    INSERT INTO ai_conversations (user_id, session_id, messages)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE SET
                        messages = (
                            SELECT to_jsonb(array_agg(m))
                            FROM (
                                SELECT m
                                FROM jsonb_array_elements(
                                    COALESCE(ai_conversations.messages, '[]'::jsonb) || EXCLUDED.messages
                                ) WITH ORDINALITY AS t(m, ord)
                                ORDER BY ord
                                OFFSET GREATEST(
                                    jsonb_array_length(
                                        COALESCE(ai_conversations.messages, '[]'::jsonb) || EXCLUDED.messages
                                    ) - %s, 0
                                )
                            ) sub
                        )
                    """,
                    (DEFAULT_USER_ID, conversation_id, Json(messages), limit),
                )

        await asyncio.to_thread(self._run, upsert)

    async def clear(self, conversation_id: str) -> None:
        await self._ensure_table()

        def delete(conn):
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM ai_conversations WHERE session_id = %s",
                    (conversation_id,),
                )

        await asyncio.to_thread(self._run, delete)

    async def list_conversations(self) -> List[ConversationSummary]:
        await self._ensure_table()

        def query(conn):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        session_id,
                        COALESCE((
                            SELECT m ->> 'content'
                            FROM jsonb_array_elements(messages) AS m
                            WHERE m ->> 'role' = 'user'
                            LIMIT 1
                        ), '') AS title,
                        EXTRACT(EPOCH FROM created_at) AS ts
                    FROM ai_conversations
                    WHERE messages IS NOT NULL AND jsonb_array_length(messages) > 0
                    ORDER BY created_at DESC
                    """
                )
                return cur.fetchall()

        rows = await asyncio.to_thread(self._run, query)
        result: List[ConversationSummary] = []
        for sid, title, ts in rows:
            clean = (title or "").strip().replace("\n", " ")[:30] or "新对话"
            result.append({
                "conversation_id": sid,
                "title": clean,
                "updated_at": float(ts or 0.0),
            })
        return result


# =============================================================================
# 报告产出回写：把一次健康决策的结果存到同一 ai_conversations 行
# =============================================================================
def _save_artifacts_sync(session_id: str, user_id: int, result: Dict[str, Any]) -> None:
    training_plan = result.get("training_plan", {})
    meal_plan = result.get("meal_plan", {})
    safety = result.get("safety_result", {})
    speech = (result.get("final_report", {}) or {}).get("vocal_narrative", "")
    agent_decisions = {
        "reasoning_chain": result.get("reasoning_chain", []),
        "agent_outputs": result.get("agent_outputs", {}),
        "derived_metrics": result.get("derived_metrics", {}),
        "data_sources": result.get("data_sources", {}),
    }
    recommendations = {
        "physio_assessment": result.get("physio_assessment", {}),
        "sleep_advice": result.get("sleep_advice", {}),
        "final_report": result.get("final_report", {}),
        "mode": result.get("mode"),
        "fatigue_level": result.get("fatigue_level"),
    }

    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(_ENSURE_INDEX_SQL)
            cur.execute(
                """
                INSERT INTO ai_conversations
                    (user_id, session_id, agent_decisions, safety_logs,
                     recommendations, training_plan, meal_plan, speech_report)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    agent_decisions = EXCLUDED.agent_decisions,
                    safety_logs     = EXCLUDED.safety_logs,
                    recommendations = EXCLUDED.recommendations,
                    training_plan   = EXCLUDED.training_plan,
                    meal_plan       = EXCLUDED.meal_plan,
                    speech_report   = EXCLUDED.speech_report
                """,
                (user_id, session_id, Json(agent_decisions), Json(safety),
                 Json(recommendations), Json(training_plan), Json(meal_plan), speech),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


async def save_assessment_artifacts(session_id: str, user_id: int, result: Dict[str, Any]) -> None:
    """异步回写健康决策产出到 ai_conversations（同 session_id 行）。"""
    await asyncio.to_thread(_save_artifacts_sync, session_id, user_id, result)


# =============================================================================
# 读取某用户最近一次已生成的报告（供 /report/latest 复用，免重复跑工作流）
# =============================================================================
def _load_latest_sync(user_id: int):
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT session_id, recommendations, agent_decisions, safety_logs,
                       training_plan, meal_plan, speech_report, created_at
                FROM ai_conversations
                WHERE user_id = %s AND training_plan IS NOT NULL
                ORDER BY created_at DESC LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
        return dict(row) if row else None
    finally:
        pool.putconn(conn)


async def load_latest_assessment(user_id: int) -> Dict[str, Any]:
    """读取并还原某用户最近一次报告为 run_health_assessment 同构结构（无则返回 None）。"""
    row = await asyncio.to_thread(_load_latest_sync, user_id)
    if not row:
        return None
    rec = row.get("recommendations") or {}
    ad = row.get("agent_decisions") or {}
    return {
        "success": True,
        "source": "cache",                       # 标记来自落库缓存，非实时工作流
        "session_id": row.get("session_id"),
        "mode": rec.get("mode"),
        "fatigue_level": rec.get("fatigue_level"),
        "physio_assessment": rec.get("physio_assessment", {}),
        "sleep_advice": rec.get("sleep_advice", {}),
        "training_plan": row.get("training_plan") or {},
        "meal_plan": row.get("meal_plan") or {},
        "safety_result": row.get("safety_logs") or {},
        "final_report": rec.get("final_report", {}),
        "reasoning_chain": ad.get("reasoning_chain", []),
        "agent_outputs": ad.get("agent_outputs", {}),
        "derived_metrics": ad.get("derived_metrics", {}),
        "data_sources": ad.get("data_sources", {}),
        "speech_report": row.get("speech_report"),
        "created_at": str(row.get("created_at")),
        "status": "completed",
    }
