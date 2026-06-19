"""报告 Chat / 任务状态 — 面向用户的话术。"""

from datetime import date
from typing import Optional

MSG_TASK_STARTED = "正在准备你的健康数据…"
MSG_TASK_PROCESSING_EARLY = "生理指标评估中…"
MSG_TASK_PROCESSING_MID = "运动与恢复方案生成中…"
MSG_TASK_PROCESSING_LATE = "膳食建议与报告汇总中…"
MSG_TASK_COMPLETED = "报告已生成"
MSG_TASK_FAILED = "报告生成遇到问题，请稍后重试。"

WAIT_TAIL = (
    "健康顾问团队正在会诊（生理评估 → 运动建议 → 膳食方案），"
    "大约需要 1～2 分钟，请稍候…"
)
WAIT_TAIL_SHORT = "请稍候，报告正在生成中…"


def format_cn_date(iso: str, ref_today: Optional[date] = None) -> str:
    """ISO 日期 → 「今天」或「6月15日」。"""
    today = ref_today or date.today()
    d = date.fromisoformat(iso)
    if d == today:
        return "今天"
    return f"{d.month}月{d.day}日"


def progress_message(status: str, progress: int) -> str:
    """按任务 status/progress 返回用户向进度句。"""
    if status == "started":
        return MSG_TASK_STARTED
    if status != "processing":
        return MSG_TASK_STARTED
    if progress < 40:
        return MSG_TASK_PROCESSING_EARLY
    if progress < 70:
        return MSG_TASK_PROCESSING_MID
    return MSG_TASK_PROCESSING_LATE


def immediate_reply(anchor_date: str, routed_reply: Optional[str] = None) -> str:
    """report 意图即时 ChatResponse.reply（不含 task_id）。"""
    day_label = format_cn_date(anchor_date)
    lead = (routed_reply or f"好的，正在为你生成{day_label}的健康体检报告。").strip()
    tail = WAIT_TAIL_SHORT if len(lead) > 120 else WAIT_TAIL
    return f"{lead}\n\n{tail}"
