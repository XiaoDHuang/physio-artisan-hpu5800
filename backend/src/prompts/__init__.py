"""
提示词模块
"""

from .system_prompt import SYSTEM_PROMPT, contains_injection_attempt

__all__ = ["SYSTEM_PROMPT", "contains_injection_attempt"]
