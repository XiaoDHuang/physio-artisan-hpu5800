"""会话历史存储模块。

提供「服务端维护对话历史」的存储抽象：
- ConversationStore        : 存储接口（抽象基类）
- InMemoryConversationStore: 默认的进程内内存实现
- get_store()              : 全局单例工厂

设计目标：把存储细节收敛到本模块。/chat 接口只依赖 ConversationStore 接口，
将来要换成 PostgreSQL（项目已有 ai_conversations 表）等持久化实现时，
只需新增一个实现类并在 get_store() 中返回，业务代码无需改动。

消息统一格式：{"role": "user" | "assistant" | "system", "content": str}
"""

from __future__ import annotations

import asyncio
import os
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List, Optional, TypedDict


# 每个会话默认保留的「轮」数（1 轮 = 1 条 user + 1 条 assistant）。
# 超出后丢弃最早的记录，用于控制上下文长度与大模型 token 成本。
DEFAULT_MAX_TURNS = 20


class ConversationSummary(TypedDict):
    """会话列表项：用于左侧历史栏展示。"""
    conversation_id: str
    title: str           # 取首条 user 消息的前若干字符
    updated_at: float    # Unix 时间戳（秒），便于前端排序/格式化


def _make_title(messages: List[Dict[str, str]]) -> str:
    """从消息列表生成标题：取首条 user 消息，截断到 30 字。"""
    for m in messages:
        if m.get("role") == "user":
            text = (m.get("content") or "").strip().replace("\n", " ")
            return text[:30] or "新对话"
    return "新对话"


class ConversationStore(ABC):
    """会话历史存储接口。

    实现类需保证 get_history / append / clear / list_conversations 在并发协程下的安全性。
    """

    @abstractmethod
    async def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """返回指定会话的历史消息列表（不含本轮新消息）；会话不存在时返回空列表。"""
        raise NotImplementedError

    @abstractmethod
    async def append(self, conversation_id: str, messages: List[Dict[str, str]]) -> None:
        """向指定会话追加一条或多条消息（通常是本轮的 user + assistant）。"""
        raise NotImplementedError

    @abstractmethod
    async def clear(self, conversation_id: str) -> None:
        """清空（删除）指定会话的历史。会话不存在时应静默成功。"""
        raise NotImplementedError

    @abstractmethod
    async def list_conversations(self) -> List[ConversationSummary]:
        """列出所有会话摘要，按最近更新时间倒序。"""
        raise NotImplementedError


class InMemoryConversationStore(ConversationStore):
    """基于进程内字典的会话历史存储（默认实现）。

    优点：零外部依赖、读写极快。
    缺点：服务重启即丢失、多进程/多实例之间不共享。
    适用：本地开发、单实例部署、演示。

    Args:
        max_turns: 每个会话保留的最大轮数，超出后裁剪最早的消息。
    """

    def __init__(self, max_turns: int = DEFAULT_MAX_TURNS) -> None:
        self._data: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self._updated_at: Dict[str, float] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._max_messages = max(1, max_turns) * 2

    async def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        async with self._locks[conversation_id]:
            # 返回副本，避免调用方在锁外修改内部列表
            return list(self._data.get(conversation_id, []))

    async def append(self, conversation_id: str, messages: List[Dict[str, str]]) -> None:
        if not messages:
            return
        async with self._locks[conversation_id]:
            history = self._data[conversation_id]
            history.extend(messages)
            # 滑动窗口裁剪：只保留最近 _max_messages 条
            overflow = len(history) - self._max_messages
            if overflow > 0:
                del history[:overflow]
            self._updated_at[conversation_id] = time.time()

    async def clear(self, conversation_id: str) -> None:
        async with self._locks[conversation_id]:
            self._data.pop(conversation_id, None)
            self._updated_at.pop(conversation_id, None)

    async def list_conversations(self) -> List[ConversationSummary]:
        items: List[ConversationSummary] = [
            {
                "conversation_id": cid,
                "title": _make_title(msgs),
                "updated_at": self._updated_at.get(cid, 0.0),
            }
            for cid, msgs in self._data.items()
            if msgs
        ]
        items.sort(key=lambda x: x["updated_at"], reverse=True)
        return items


# --------------------------- 全局单例 ---------------------------
_store: Optional[ConversationStore] = None


def get_store() -> ConversationStore:
    """获取全局会话存储单例。

    由环境变量 CONVERSATION_STORE 决定后端实现：
    - "memory"（默认）：进程内内存，零依赖，重启即丢。
    - "postgres"：持久化到 PostgreSQL（hpu_db.chat_conversations）。

    切换实现只需改 .env，业务代码（/chat 等）无需改动。
    """
    global _store
    if _store is None:
        backend = os.getenv("CONVERSATION_STORE", "memory").strip().lower()
        if backend == "postgres":
            from .postgres_store import PostgresConversationStore
            _store = PostgresConversationStore()
        else:
            _store = InMemoryConversationStore()
    return _store
