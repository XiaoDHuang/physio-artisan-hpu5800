"""
数据库模块
统一使用 PostgreSQL
"""

from .models import (
    # 表模型
    Base,
    User,
    WatchData,
    ExerciseRecord,
    NutritionLog,
    AIConversation,
    PromptTemplate,
    SafetyLog,
    # 初始化函数
    get_database_url,
    init_database,
    get_session,
    create_tables,
    seed_prompt_templates,
    DEFAULT_PROMPTS
)

from .postgres import (
    PostgresConfig,
    init_postgres,
    check_connection,
    INSTALL_GUIDE
)

from .vector_db import VectorDB, HPURecommender

__all__ = [
    # 表模型
    "Base",
    "User",
    "WatchData",
    "ExerciseRecord",
    "NutritionLog",
    "AIConversation",
    "PromptTemplate",
    "SafetyLog",
    
    # 初始化函数
    "get_database_url",
    "init_database",
    "get_session",
    "create_tables",
    "seed_prompt_templates",
    "DEFAULT_PROMPTS",
    
    # PostgreSQL配置
    "PostgresConfig",
    "init_postgres",
    "check_connection",
    "INSTALL_GUIDE",
    
    # 向量数据库
    "VectorDB",
    "HPURecommender"
]
