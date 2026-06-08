"""
「暴汗艺术家」安全审计封装（启用真实拦截）

在既有 src/safety/guardrails.py（SafetyGuardrails 四层检测）基础上：
1. 合并设计方案的药物红线词全集（GUARDRAIL_FORBIDDEN_TERMS）到处方药维度；
2. 提供统一的 screen_text() 返回归一化结果，供 /chat 输入预检与
   guardrail_auditor 输出审计共用；
3. 命中时给出熔断话术（设计方案安全熔断模板）。

适用于大模型技术初级用户：
- "防御纵深(defense in depth)" = 在输入侧与输出侧都设卡，任一层拦住即生效。
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.safety.guardrails import get_safety_guardrails  # noqa: E402
from agents.health_prompts import GUARDRAIL_FORBIDDEN_TERMS, GUARDRAIL_BLOCK_TEMPLATE  # noqa: E402

logger = logging.getLogger("health_agents")

_MERGED = False


def _ensure_redlines() -> None:
    """把设计方案药物红线词合并进 SafetyGuardrails 的处方药维度（幂等）。"""
    global _MERGED
    if _MERGED:
        return
    guard = get_safety_guardrails()
    presc = guard.MEDICAL_FORBIDDEN.setdefault("prescription", [])
    for term in GUARDRAIL_FORBIDDEN_TERMS:
        if term not in presc:
            presc.append(term)
    _MERGED = True


def screen_text(text: str) -> Dict[str, Any]:
    """对一段文本做安全筛查，返回归一化结果。

    Returns: {
        "is_safe": bool, "blocked": bool, "category": str, "level": str,
        "violations": [...], "warnings": [...], "block_message": str|""
    }
    """
    _ensure_redlines()
    guard = get_safety_guardrails()
    r = guard.check(text or "")

    blocked = not r.is_safe
    block_message = ""
    if blocked:
        # 优先用设计方案的就医分流熔断模板；其余类别用护栏内置话术
        if r.category in ("medical", "injection", "inappropriate", "privacy"):
            block_message = GUARDRAIL_BLOCK_TEMPLATE if r.category == "medical" \
                else guard.generate_fallback_response(r.category).strip()
        else:
            block_message = GUARDRAIL_BLOCK_TEMPLATE

    return {
        "is_safe": r.is_safe,
        "blocked": blocked,
        "category": r.category,
        "level": r.level.value,
        "violations": r.violations,
        "warnings": r.warnings,
        "block_message": block_message,
    }
