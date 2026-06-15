"""
plan_adapter —— 把 /plan 产出的 result dict 转换为 v3.1 user_plans 三计划 JSON。

纯函数 + .get 容错；落库失败由上游 return False，不抛异常。
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger("health_agents")


def _parse_range_upper(val: Any) -> Optional[int]:
    """解析区间上限，"40-60"→60、"320-450"→450；失败返回 None。"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        m = re.search(r"\d+$", val.strip())
        if m:
            return int(m.group())
    return None


def _pick(obj: Any, *keys: str, default: Any = None) -> Any:
    """从嵌套 dict 取第一个存在的键；全部不存在返回 default。"""
    if not isinstance(obj, dict):
        return default
    for k in keys:
        v = obj.get(k)
        if v is not None:
            return v
    return default


def to_user_plans(result: dict, plan_date: str) -> Dict[str, Any]:
    """将一个 /plan result 转为 user_plans 三计划。

    Args:
        result: run_health_assessment 返回的完整 result dict
        plan_date: 计划日 YYYY-MM-DD（通常为今天）

    Returns:
        {"training_plan": {...}, "sleep_plan": {...}, "diet_plan": {...}}
    """
    # ---- training_plan ----
    tp = result.get("training_plan") or {}
    tp_exercises_raw = tp.get("exercises") or []
    tp_exercises: List[Dict[str, Any]] = []
    for ex in tp_exercises_raw:
        if not isinstance(ex, dict):
            continue
        name = ex.get("name", "训练")
        item: Dict[str, Any] = {"name": name, "intensity": "medium"}
        # external_id
        eid = ex.get("external_id")
        if eid is not None:
            item["external_id"] = eid
        else:
            item["external_id"] = None
        item["external_source"] = "wger"
        # 组数×次数 或 时长
        if ex.get("sets") is not None and ex.get("reps") is not None:
            item["sets"] = ex["sets"]
            item["reps"] = ex["reps"]
        elif ex.get("duration_sec") is not None:
            dur_sec = ex["duration_sec"]
            item["duration"] = f"{int(dur_sec) // 60}分钟" if dur_sec >= 60 else f"{int(dur_sec)}秒"
        elif ex.get("duration") is not None:
            item["duration"] = str(ex["duration"])
        else:
            # 保底：至少含 name，不影响页面渲染
            pass
        # 强制必须有 (sets & reps) 或 duration 之一（预防渲染 null）
        if "sets" not in item and "reps" not in item and "duration" not in item:
            item["sets"] = 3
            item["reps"] = 12
        tp_exercises.append(item)

    # safety_flags from safety_result
    sr = result.get("safety_result") or {}
    safety_flags: List[Dict[str, str]] = []
    if sr.get("status") == "blocked":
        safety_flags = [{"level": "block", "message": sr.get("final_text") or sr.get("message", "") or "安全熔断，建议就医"}]

    target_dur = _parse_range_upper(tp.get("recommended_duration"))
    target_kcal = _parse_range_upper(tp.get("calorie_target"))

    training_plan = {
        "date": plan_date,
        "training_type": tp.get("training_type") or "recovery",
        "reason": tp.get("reason") or "",
        "target_rpe": None,
        "target_duration_min": target_dur,
        "target_total_kcal": target_kcal,
        "target_avg_hr": None,
        "target_peak_hr": None,
        "exercises": tp_exercises,
        "safety_flags": safety_flags,
    }

    # ---- sleep_plan ----
    sa = result.get("sleep_advice") or {}
    sa_advice = sa.get("advice") or ""
    sa_focus = sa.get("focus") or ""
    # suggestion title: focus 优先；action: 完整 advice
    title = sa_focus or (sa_advice[:40] + "…" if len(sa_advice) > 40 else sa_advice) or "保持规律作息"
    suggestions = [{
        "title": title,
        "category": "routine",
        "action": sa_advice or title,
    }]

    sleep_plan = {
        "date": plan_date,
        "target_bedtime": None,
        "target_wake_time": None,
        "target_duration_h": None,
        "target_sleep_score": None,
        "suggestions": suggestions,
    }

    # ---- diet_plan ----
    mp = result.get("meal_plan") or {}
    mp_meals_raw = mp.get("meals") or []
    diet_meals: List[Dict[str, Any]] = []
    for m in mp_meals_raw:
        if not isinstance(m, dict):
            continue
        foods = []
        for f in (m.get("foods") or []):
            if not isinstance(f, dict):
                continue
            foods.append({
                "name": f.get("name", "食材"),
                "external_id": f.get("external_id"),
                "external_source": f.get("external_source", "usda"),
                "amount_g": f.get("grams", 0),
                "calories": f.get("calories", 0),
                "protein_g": f.get("protein", 0),
            })
        diet_meals.append({
            "meal": m.get("meal", "餐"),
            "foods": foods,
        })

    sauce_comp = mp.get("sauce_compensation")
    diet_plan = {
        "date": plan_date,
        "total_calories_target": mp.get("total_calories"),
        "macros": {
            "protein_g": mp.get("protein_target_g"),
            "carbs_g": None,
            "fat_g": None,
        },
        "meals": diet_meals,
        "notes": mp.get("diet_suggestion") or "",
        "sauce_compensation_applied": bool(sauce_comp and sauce_comp > 1.0),
        "sauce_factor": sauce_comp,
    }

    return {
        "training_plan": training_plan,
        "sleep_plan": sleep_plan,
        "diet_plan": diet_plan,
    }
