"""后端自包含的 PostgreSQL 连接配置。

读取 backend/.env 中的 PG_* 变量，不依赖项目根目录或 src/。
后端整体迁移时随 backend/ 一起移动，零改动。

连接优先级：
1. DATABASE_URL（如设置）
2. PG_HOST / PG_PORT / PG_DATABASE / PG_USER / PG_PASSWORD
3. 源码默认值（localhost:5432/hpu_db, postgres）
"""

import os
from functools import lru_cache
from urllib.parse import urlparse

from dotenv import load_dotenv

# 显式加载 backend/.env（与本文件同属 backend 包的上级目录）
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_ENV_PATH)


def get_connection_params() -> dict:
    """返回 psycopg2 连接参数字典。"""
    url = os.getenv("DATABASE_URL")
    if url:
        parsed = urlparse(url)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "dbname": parsed.path.lstrip("/") or "hpu_db",
            "user": parsed.username or "postgres",
            "password": parsed.password or "",
        }
    return {
        "host": os.getenv("PG_HOST", "localhost"),
        "port": int(os.getenv("PG_PORT", "5432")),
        "dbname": os.getenv("PG_DATABASE", "hpu_db"),
        "user": os.getenv("PG_USER", "postgres"),
        "password": os.getenv("PG_PASSWORD", ""),
    }


@lru_cache(maxsize=1)
def get_pool():
    """创建并缓存一个线程安全的连接池（首次调用时初始化）。"""
    from psycopg2.pool import ThreadedConnectionPool

    params = get_connection_params()
    return ThreadedConnectionPool(minconn=1, maxconn=10, **params)
