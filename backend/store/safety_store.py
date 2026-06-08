"""安全日志持久化：把安全审计结果写入 hpu_db.safety_logs 表。

阻塞式 psycopg2 调用通过 asyncio.to_thread 放到线程池执行；
也提供同步入口供 LangGraph 节点（线程池内）直接调用。
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from psycopg2.extras import Json

from .db import get_pool

DEFAULT_USER_ID = 1


def save_safety_log_sync(input_text: str, category: str, level: str,
                         violations: List[str], warnings: List[str],
                         blocked: bool, user_id: Optional[int] = DEFAULT_USER_ID) -> None:
    """同步写入一条安全日志。"""
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO safety_logs
                    (user_id, input_text, category, level, violations, warnings, blocked)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, (input_text or "")[:2000], category, level,
                 Json(violations or []), Json(warnings or []), 1 if blocked else 0),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


async def save_safety_log(input_text: str, category: str, level: str,
                          violations: List[str], warnings: List[str],
                          blocked: bool, user_id: Optional[int] = DEFAULT_USER_ID) -> None:
    """异步写入一条安全日志。"""
    await asyncio.to_thread(
        save_safety_log_sync, input_text, category, level, violations, warnings, blocked, user_id
    )
