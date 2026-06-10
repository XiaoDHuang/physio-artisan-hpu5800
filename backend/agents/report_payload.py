"""
「暴汗艺术家」报告数据契约（chart_data）

渲染交由前端：本模块只产出"图表就绪"的结构化数据，不在 Python 端画图/合成语音。
对应设计方案 §5 多模态体检报告的四块：
- rs_gauge      : 准备度半圆仪表盘（数值 + 色阶 + 疲劳等级）
- trend_dual    : HRV & 身体年龄 7 日双曲线（control 放任恶化 vs experiment 积极恢复）
- radar_compare : 干预前后健康雷达（多维 0-100 归一化）
- cards         : 今日训练 / 今日餐盘（直接给前端渲染的 JSON）

数据来源：对 control / experiment 两套场景分别调用 health_data.compute_metrics，
据此生成对照-实验对比序列；端点值对齐设计方案 §6 答辩核心数据表。

适用于大模型技术初级用户：
- "数据契约" = 前后端约定好的字段结构，前端拿到后用 ECharts/Recharts 等自行绘制。
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List

from agents import health_data as hdata

logger = logging.getLogger("health_agents")

# 7 日趋势端点（设计方案 §2.3 / §6）：起点相同，放任 vs 采纳分别走向两端
_TREND_DAYS = 7
_TREND_ENDPOINTS = {
    "hrv": {"start": 45.0, "control": 32.0, "experiment": 45.0},        # control 暴跌 / experiment 恢复
    "body_age": {"start": 35.0, "control": 35.5, "experiment": 34.6},   # control 老化 / experiment 年轻化
}


def _series(start: float, end: float, n: int = _TREND_DAYS) -> List[float]:
    """在 start..end 之间线性插值出 n 个点（保留 1 位小数）。"""
    if n <= 1:
        return [round(end, 1)]
    step = (end - start) / (n - 1)
    return [round(start + step * i, 1) for i in range(n)]


def _norm(value: float, lo: float, hi: float) -> float:
    """把 value 线性归一化到 0-100（用于雷达图）。"""
    if hi == lo:
        return 0.0
    return round(max(0.0, min(100.0, (value - lo) / (hi - lo) * 100)), 1)


def _radar_dims(derived: Dict[str, Any], snap: Dict[str, Any]) -> List[float]:
    """把一套场景指标换算成雷达 5 维分值（越高越好，0-100）。"""
    sleep = _norm(snap.get("sleep_score", 0), 40, 100)        # 睡眠评分
    hrv = _norm(snap.get("hrv_today", 0), 20, 60)             # HRV
    hrr = _norm(derived.get("hrr", 0), 5, 25)                 # 心率恢复力
    rs = _norm(derived.get("rs", 0), 40, 100)                # 准备度
    body_fat = _norm(40 - snap.get("body_fat_pct", 25), 10, 25)  # 体脂(反向: 越低分越高)
    return [sleep, hrv, hrr, rs, body_fat]


def build_report_payload(user_id: int, result: Dict[str, Any]) -> Dict[str, Any]:
    """根据一次评估结果，生成前端渲染所需的 chart_data。

    Args:
        user_id: 用户ID（用于拉取双场景数据）。
        result: run_health_assessment 的返回值（含 derived_metrics / training_plan 等）。
    """
    try:
        ctrl = hdata.compute_metrics(user_id, "control")
        expt = hdata.compute_metrics(user_id, "experiment")
    except Exception as e:  # noqa: BLE001
        logger.error("[report_payload] 双场景指标计算失败: %s", e)
        ctrl = expt = None

    d = result.get("derived_metrics", {})
    rs = d.get("rs", 0)
    fatigue = result.get("fatigue_level", "low")

    # ① RS 半圆仪表盘
    rs_gauge = {
        "value": rs,
        "min": 0, "max": 100,
        "fatigue": fatigue,
        "zones": [
            {"label": "高疲劳", "range": [0, 55], "color": "#DC3545"},
            {"label": "中疲劳", "range": [55, 75], "color": "#FFC107"},
            {"label": "良好", "range": [75, 100], "color": "#28A745"},
        ],
    }

    # ② HRV & 身体年龄 7 日双曲线
    trend_dual = {
        "days": [f"D{i + 1}" for i in range(_TREND_DAYS)],
        "hrv": {
            "control": _series(_TREND_ENDPOINTS["hrv"]["start"], _TREND_ENDPOINTS["hrv"]["control"]),
            "experiment": _series(_TREND_ENDPOINTS["hrv"]["start"], _TREND_ENDPOINTS["hrv"]["experiment"]),
            "unit": "ms",
        },
        "body_age": {
            "control": _series(_TREND_ENDPOINTS["body_age"]["start"], _TREND_ENDPOINTS["body_age"]["control"]),
            "experiment": _series(_TREND_ENDPOINTS["body_age"]["start"], _TREND_ENDPOINTS["body_age"]["experiment"]),
            "unit": "岁",
        },
        "legend": {"control": "放任恶化(灰虚线)", "experiment": "采纳建议(绿实线)"},
    }

    # ③ 干预前后健康雷达
    radar_compare = {
        "dimensions": ["睡眠", "HRV", "心率恢复", "准备度", "体脂(反向)"],
        "control": _radar_dims(ctrl["derived"], ctrl["snapshot"]) if ctrl else [],
        "experiment": _radar_dims(expt["derived"], expt["snapshot"]) if expt else [],
        "legend": {"control": "干预前", "experiment": "干预后"},
    }

    # ④ 今日训练 / 餐盘 / 睡眠建议 / 生理 卡片（直接给前端渲染）
    #    health_advice = 运动/睡眠/饮食 三张建议卡的文本（对应 UI"健康建议"区）
    cards = {
        "training": result.get("training_plan", {}),
        "meal": result.get("meal_plan", {}),
        "sleep": result.get("sleep_advice", {}),
        "physio": result.get("physio_assessment", {}),
        "health_advice": {
            "exercise": (result.get("training_plan", {}) or {}).get("reason", ""),
            "sleep": (result.get("sleep_advice", {}) or {}).get("advice", ""),
            "nutrition": (result.get("meal_plan", {}) or {}).get("diet_suggestion", ""),
        },
    }

    # ⑤ 仪表盘各面板（来自数据库真实周聚合）：身体概览/睡眠/饮食/运动/周对比/KPI
    try:
        dashboard = hdata.get_week_overview(user_id)
    except Exception as e:  # noqa: BLE001
        logger.error("[report_payload] 周聚合失败: %s", e)
        dashboard = {}

    return {
        "rs_gauge": rs_gauge,
        "trend_dual": trend_dual,
        "radar_compare": radar_compare,
        "cards": cards,
        "visual_metrics": (result.get("final_report", {}) or {}).get("visual_metrics", {}),
        "dashboard": dashboard,
    }
