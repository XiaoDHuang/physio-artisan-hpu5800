"""
Langfuse 可观测性接入（大模型链路追踪）

把「暴汗艺术家」多智能体工作流的每一次 LLM 调用，以 LangChain
`CallbackHandler` 的形式上报到 Langfuse，形成一条 trace：
- 一次 `run_health_assessment` = 一条 trace（名为 health_assessment）
- 五个智能体的 `llm.invoke()` = trace 下的若干 generation（自动嵌套）
- 携带 user_id / session_id / mode 标签，便于在控制台筛选与成本分析

设计原则（与方案评审一致）：
- 仅追踪 LLM 调用，不单独上报 wger/USDA/safety 等工具 span（零侵入节点逻辑）。
- 静默降级：未装包 / host 不通 / key 缺失，一律记一条 warning 后照常运行，
  追踪失败绝不影响业务工作流。

使用方式见 langgraph_agents.py：
    client = get_langfuse_client()
    handler, _ = build_callback_handler(client)
    graph.invoke(state, config=build_run_config(handler, user_id, mode, session_id))
    ...
    flush_langfuse(client)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from config.langgraph_config import langgraph_config as config

logger = logging.getLogger("health_agents")

# 进程级单例：Langfuse 客户端只初始化一次（None 表示未启用/初始化失败）
_langfuse_client: Optional[Any] = None
_init_attempted = False


def get_langfuse_client() -> Optional[Any]:
    """获取（惰性初始化）Langfuse 客户端单例。

    返回 None 表示追踪未启用或初始化失败 —— 调用方据此静默降级。
    """
    global _langfuse_client, _init_attempted
    if _init_attempted:
        return _langfuse_client
    _init_attempted = True

    if not config.is_langfuse_enabled():
        logger.info("[Langfuse] 未启用（开关关闭或缺少 public/secret key），跳过追踪。")
        return None

    try:
        from langfuse import Langfuse  # 延迟导入：未装包时不影响主流程
        cfg = config.get_langfuse_config()
        _langfuse_client = Langfuse(
            public_key=cfg["public_key"],
            secret_key=cfg["secret_key"],
            host=cfg["host"],
        )
        logger.info("[Langfuse] 客户端初始化成功 host=%s", cfg["host"])
    except Exception as e:  # noqa: BLE001
        logger.warning("[Langfuse] 初始化失败，已降级为无追踪运行: %s", e)
        _langfuse_client = None
    return _langfuse_client


def build_callback_handler(client: Optional[Any]) -> Tuple[Optional[Any], Dict[str, Any]]:
    """基于已初始化的客户端构造 LangChain CallbackHandler。

    Returns:
        (handler, meta)：client 为 None 或构造失败时返回 (None, {})。
    """
    if client is None:
        return None, {}
    try:
        # Langfuse v3：CallbackHandler 不再接收 key，复用全局已初始化的客户端。
        # update_trace=True 让根运行的 run_name / metadata(session/user/tags) 提升到 trace 层，
        # 使控制台中该 trace 命名为 health_assessment 并带上会话/用户标签。
        from langfuse.langchain import CallbackHandler
        return CallbackHandler(update_trace=True), {}
    except Exception as e:  # noqa: BLE001
        logger.warning("[Langfuse] CallbackHandler 构造失败，已降级: %s", e)
        return None, {}


def build_run_config(
    handler: Optional[Any],
    *,
    user_id: Any,
    mode: str,
    session_id: str = "",
    tags: Optional[List[str]] = None,
    run_name: str = "health_assessment",
) -> Optional[Dict[str, Any]]:
    """组装传给 graph.invoke 的 RunnableConfig。

    handler 为 None 时返回 None —— 即不带任何回调，工作流行为与接入前完全一致。
    """
    if handler is None:
        return None
    base_tags = [str(mode), "langgraph", "physio-artisan"]
    if tags:
        base_tags.extend(tags)
    return {
        "callbacks": [handler],
        "run_name": run_name,
        "metadata": {
            "langfuse_user_id": str(user_id),
            "langfuse_session_id": session_id or "",
            "langfuse_tags": base_tags,
        },
    }


def flush_langfuse(client: Optional[Any]) -> None:
    """best-effort 刷新缓冲区（批处理任务结束后确保事件落库）。"""
    if client is None:
        return
    try:
        client.flush()
    except Exception as e:  # noqa: BLE001
        logger.warning("[Langfuse] flush 失败（忽略）: %s", e)
