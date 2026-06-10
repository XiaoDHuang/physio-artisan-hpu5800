"""
「暴汗艺术家」健康智能体 - 数据接入层（DB 优先 + mock 回退）

职责（对应设计方案"数据接入层"）：
- 以 **PostgreSQL hpu_db 为准**读取用户画像与穿戴/运动/饮食原始指标；
- 当库中数据缺失（如 exercise_records / nutrition_logs 为空、watch_data 仅一行无基线、
  无对照/实验两套序列）时，**自动回退到设计方案 §8 的 mock 协议数据**，
  保证编排在任何环境下都能跑通；
- 通过 `mode = control | experiment` 选择"放任恶化"或"积极恢复"两套演示场景。

返回的是**原始/半成品指标**，真正的 RS / HRR / TRIMP / 疲劳红旗由 health_tools 的
确定性公式计算，体现"结合下游工具指标输入计算"的设计意图。

适用于大模型技术初级用户：
- "回退(fallback)" = 首选方案不可用时退而求其次，是健壮系统的常见做法。
- 字段含义见设计方案 §2.2 与 §8 的数据协议。
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("health_agents")


# =============================================================================
# 一、设计方案 §8 的 mock 场景数据（对照组 / 实验组）
#     当数据库缺数据时作为回退；mode 也直接命中这两套场景。
# =============================================================================

MOCK_SCENARIOS: Dict[str, Dict[str, Any]] = {
    # ① 对照组——放任恶化路径（高疲劳，触发降载干预）
    "control": {
        "watch": {"sleep_score": 58, "hrv_today": 32.0, "rhr_today": 75, "rhr_trend_up_3d": True},
        "exercise": {"duration_minutes": 90, "peak_hr": 175, "hr_60s": 163, "rpe": 9},
        "diet": {"diet_narrative": "早餐：油条2根，甜豆浆。午餐：凯撒沙拉多加酱，红烧肉盖饭。"
                                    "晚餐：炸鸡啤酒，宵夜方便面加火腿肠。"},
        "body": {"weight_kg": 80.5, "body_fat_pct": 24.0},
    },
    # ② 实验组——积极恢复路径（疲劳消除，维持/正向）
    "experiment": {
        "watch": {"sleep_score": 82, "hrv_today": 45.0, "rhr_today": 63, "rhr_trend_up_3d": False},
        "exercise": {"duration_minutes": 30, "peak_hr": 130, "hr_60s": 110, "rpe": 4},
        "diet": {"diet_narrative": "早餐：无糖希腊酸奶200g，坚果，蓝莓。午餐：香煎鸡胸肉150g，糙米饭，"
                                    "水煮西蓝花。晚餐：香煎三文鱼150g，藜麦沙拉。"},
        "body": {"weight_kg": 79.5, "body_fat_pct": 23.5},
    },
}

# 默认用户画像（库不可用时回退到设计方案小明画像）
MOCK_PROFILE = {
    "id": 1, "name": "小明", "age": 30, "gender": "male",
    "height_cm": 175.0, "weight_kg": 80.0, "goal": "lose_weight",
    "activity_level": "moderate",
}


def _normalize_mode(mode: Optional[str]) -> str:
    m = (mode or "control").lower()
    return m if m in MOCK_SCENARIOS else "control"


# =============================================================================
# 二、数据库读取（基于 store.db 连接池），任一步失败均回退 mock
# =============================================================================

def _query_one(sql: str, params: tuple) -> Optional[Dict[str, Any]]:
    """执行单行查询，返回 dict；DB 不可用时返回 None。"""
    try:
        from store.db import get_pool
        import psycopg2.extras
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
            return dict(row) if row else None
        finally:
            pool.putconn(conn)
    except Exception as e:  # noqa: BLE001
        logger.debug("[health_data] DB 查询失败, 回退 mock: %s", e)
        return None


def _query_all(sql: str, params: tuple) -> List[Dict[str, Any]]:
    try:
        from store.db import get_pool
        import psycopg2.extras
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            pool.putconn(conn)
    except Exception as e:  # noqa: BLE001
        logger.debug("[health_data] DB 批量查询失败, 回退 mock: %s", e)
        return []


# =============================================================================
# 三、对外接口
# =============================================================================

def get_user_profile(user_id: int) -> Dict[str, Any]:
    """读取用户画像；库无记录则回退 mock 小明画像。"""
    row = _query_one(
        "SELECT id, name, age, gender, height_cm, weight_kg, goal, activity_level, "
        "body_fat_pct, muscle_mass_kg, goals "
        "FROM users WHERE id = %s",
        (user_id,),
    )
    if row:
        row["_source"] = "db"
        return row
    logger.info("[health_data] users 无 id=%s, 使用 mock 画像", user_id)
    p = dict(MOCK_PROFILE)
    p["_source"] = "mock"
    return p


def _compute_baselines(user_id: int) -> Dict[str, Optional[float]]:
    """从历史 watch_data（排除最新一行）估算个人基线；样本不足返回 None。"""
    rows = _query_all(
        "SELECT heart_rate_rest, hrv_data FROM watch_data "
        "WHERE user_id = %s ORDER BY date DESC LIMIT 8",
        (user_id,),
    )
    # 至少需要 2 条历史(除今日)才能算基线
    hist = rows[1:] if len(rows) >= 2 else []
    if not hist:
        return {"hrv_baseline": None, "rhr_baseline": None}
    rhr_vals = [r["heart_rate_rest"] for r in hist if r.get("heart_rate_rest")]
    hrv_vals = [(r.get("hrv_data") or {}).get("rmssd") for r in hist]
    hrv_vals = [v for v in hrv_vals if v]
    return {
        "hrv_baseline": round(sum(hrv_vals) / len(hrv_vals), 1) if hrv_vals else None,
        "rhr_baseline": round(sum(rhr_vals) / len(rhr_vals)) if rhr_vals else None,
    }


def get_health_snapshot(user_id: int, mode: Optional[str] = None) -> Dict[str, Any]:
    """聚合某用户某场景下的全部原始指标，供编排层注入各智能体。

    DB 优先逐项读取（watch_data / exercise_records / nutrition_logs / users），
    任一项缺失即用 mode 对应的 mock 场景补齐，并在 `sources` 中标注每项来源。

    Returns: {
        sleep_score, hrv_today, hrv_baseline, rhr_today, rhr_baseline, rhr_trend_up_3d,
        duration_minutes, peak_hr, hr_60s, rpe,
        diet_narrative, weight_kg, body_fat_pct,
        mode, sources: {watch, exercise, diet, body, baseline}
    }
    """
    mode = _normalize_mode(mode)
    scen = MOCK_SCENARIOS[mode]
    sources: Dict[str, str] = {}

    # --- 穿戴数据：watch_data 最新一行 ---
    watch_row = _query_one(
        "SELECT date, heart_rate_rest, hrv_data, sleep_data FROM watch_data "
        "WHERE user_id = %s ORDER BY date DESC LIMIT 1",
        (user_id,),
    )
    if watch_row:
        sleep = watch_row.get("sleep_data") or {}
        hrv = watch_row.get("hrv_data") or {}
        watch = {
            "sleep_score": sleep.get("sleep_score", scen["watch"]["sleep_score"]),
            "hrv_today": hrv.get("rmssd", scen["watch"]["hrv_today"]),
            "rhr_today": watch_row.get("heart_rate_rest", scen["watch"]["rhr_today"]),
            "rhr_trend_up_3d": scen["watch"]["rhr_trend_up_3d"],  # 趋势需多日历史，暂用场景值
        }
        sources["watch"] = "db"
    else:
        watch = dict(scen["watch"])
        sources["watch"] = "mock"

    # --- 个人基线：历史 watch_data 计算，不足则用工具默认基线 ---
    baselines = _compute_baselines(user_id)
    if baselines["hrv_baseline"] is not None:
        sources["baseline"] = "db"
    else:
        sources["baseline"] = "default"  # 由 health_tools 默认基线兜底

    # --- 运动负荷：exercise_records.analysis_result(JSONB) ---
    ex_row = _query_one(
        "SELECT analysis_result FROM exercise_records "
        "WHERE user_id = %s ORDER BY date DESC LIMIT 1",
        (user_id,),
    )
    ex_data = (ex_row or {}).get("analysis_result") or {}
    if ex_data:
        exercise = {
            "duration_minutes": ex_data.get("duration_minutes", scen["exercise"]["duration_minutes"]),
            "peak_hr": ex_data.get("peak_hr", scen["exercise"]["peak_hr"]),
            "hr_60s": ex_data.get("hr_60s", scen["exercise"]["hr_60s"]),
            "rpe": ex_data.get("rpe", scen["exercise"]["rpe"]),
        }
        sources["exercise"] = "db"
    else:
        exercise = dict(scen["exercise"])
        sources["exercise"] = "mock"

    # --- 饮食描述：nutrition_logs(recognized_foods/nutrition_result JSONB) ---
    nut_row = _query_one(
        "SELECT recognized_foods, nutrition_result FROM nutrition_logs "
        "WHERE user_id = %s ORDER BY date DESC LIMIT 1",
        (user_id,),
    )
    diet_narrative = None
    if nut_row:
        nr = nut_row.get("nutrition_result") or {}
        rf = nut_row.get("recognized_foods")
        diet_narrative = nr.get("diet_narrative") if isinstance(nr, dict) else None
        if not diet_narrative and rf:
            diet_narrative = "，".join(map(str, rf)) if isinstance(rf, list) else str(rf)
    if diet_narrative:
        sources["diet"] = "db"
    else:
        diet_narrative = scen["diet"]["diet_narrative"]
        sources["diet"] = "mock"

    # --- 身体测量：users.weight_kg；body_fat_pct 库内缺列，回退 mock ---
    profile = get_user_profile(user_id)
    weight_kg = profile.get("weight_kg") or scen["body"]["weight_kg"]
    body_fat_pct = scen["body"]["body_fat_pct"]  # 库无该列, 始终回退 mock
    # body 来源以体重(来自 users 画像)的真实来源为准; body_fat 恒为 mock
    sources["body"] = profile.get("_source", "mock") if profile.get("weight_kg") else "mock"

    return {
        # 穿戴
        "sleep_score": watch["sleep_score"],
        "hrv_today": watch["hrv_today"],
        "hrv_baseline": baselines["hrv_baseline"],  # None -> 工具用默认基线
        "rhr_today": watch["rhr_today"],
        "rhr_baseline": baselines["rhr_baseline"],
        "rhr_trend_up_3d": watch["rhr_trend_up_3d"],
        # 运动
        "duration_minutes": exercise["duration_minutes"],
        "peak_hr": exercise["peak_hr"],
        "hr_60s": exercise["hr_60s"],
        "rpe": exercise["rpe"],
        # 饮食 & 身体
        "diet_narrative": diet_narrative,
        "weight_kg": weight_kg,
        "body_fat_pct": body_fat_pct,
        # 元信息
        "mode": mode,
        "sources": sources,
        "profile": profile,
    }


def compute_metrics(user_id: int, mode: Optional[str] = None) -> Dict[str, Any]:
    """读取快照并用确定性公式派生全部生理指标（拒绝 LLM 口算）。

    供生理评估节点与报告数据契约（双场景对比）共同复用，避免派生逻辑漂移。

    Returns: {"snapshot": <raw snapshot>, "derived": <派生指标>}
    """
    from agents import health_tools as tools  # 延迟导入，避免循环

    snap = get_health_snapshot(user_id, mode)
    profile = snap["profile"]

    hrv_baseline = snap["hrv_baseline"] or tools.DEFAULT_HRV_BASELINE
    rhr_baseline = snap["rhr_baseline"] or tools.DEFAULT_RHR_BASELINE

    rs = tools.calc_readiness_score(
        hrv_today=snap["hrv_today"], sleep_score=snap["sleep_score"],
        rhr_today=snap["rhr_today"], hrv_baseline=hrv_baseline, rhr_baseline=rhr_baseline,
    )
    hrr = tools.calc_hrr(snap["peak_hr"], snap["hr_60s"])
    trimp = tools.calc_trimp(snap["duration_minutes"], snap["rpe"])
    flags = tools.calc_fatigue_flags(
        hrv_today=snap["hrv_today"], sleep_score=snap["sleep_score"],
        hrr=hrr, rhr_trend_up_3d=snap["rhr_trend_up_3d"], hrv_baseline=hrv_baseline,
    )
    bmi = tools.calc_bmi(snap["weight_kg"], profile.get("height_cm", 175))
    bmr = tools.calc_bmr(snap["weight_kg"], profile.get("height_cm", 175),
                         profile.get("age", 30), profile.get("gender", "male"))
    tdee = tools.calc_tdee(bmr, profile.get("activity_level", "moderate"))
    body_age = tools.calc_body_age(
        resting_hr=snap["rhr_today"], bmi=bmi,
        exercise_frequency=3, sleep_quality=snap["sleep_score"] / 10.0,
        chronological_age=profile.get("age", 30),
    )

    derived = {
        "rs": rs, "hrr": hrr, "trimp": trimp,
        "fatigue": flags["fatigue"], "flag_count": flags["count"], "flags": flags["flags"],
        "hrv_baseline": hrv_baseline, "rhr_baseline": rhr_baseline,
        "bmi": bmi, "bmr": bmr, "tdee": tdee, "body_age": body_age,
        "rhr_status": "elevated" if snap["rhr_today"] > rhr_baseline else "normal",
    }
    return {"snapshot": snap, "derived": derived}


# =============================================================================
# 仪表盘周聚合：供「健康报告」各面板取数（DB 真实历史，缺数据则返回 None/空）
# =============================================================================
def _avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def get_week_overview(user_id: int, days: int = 14) -> Dict[str, Any]:
    """聚合最近 days 天（本周+上周）数据，产出仪表盘各面板。

    返回面板：kpi / body_overview / sleep / nutrition / exercise_today / week_summary。
    无历史数据时各字段尽量回退 None，不抛异常。
    """
    from agents import health_tools as tools

    rows = _query_all(
        "SELECT date, steps, exercise_minutes, calories_burned, heart_rate_avg, "
        "heart_rate_rest, hrv_data, sleep_data FROM watch_data "
        "WHERE user_id = %s ORDER BY date DESC LIMIT %s",
        (user_id, days),
    )
    profile = get_user_profile(user_id)
    goals = profile.get("goals") or {}
    steps_goal = goals.get("steps_goal", 8000)
    ex_goal = goals.get("exercise_minutes_goal", 30)

    # 最新一天（今日面板）
    latest = rows[0] if rows else {}
    sleep = (latest.get("sleep_data") or {}) if latest else {}

    this_week = rows[:7]
    last_week = rows[7:14]

    def _week_stats(wk):
        if not wk:
            return {"workout_days": 0, "total_burn": 0, "avg_sleep": None,
                    "avg_steps": None, "ex_rate": 0, "score": None}
        workout_days = sum(1 for r in wk if (r.get("exercise_minutes") or 0) >= ex_goal)
        total_burn = sum(r.get("calories_burned") or 0 for r in wk)
        avg_sleep = _avg([(r.get("sleep_data") or {}).get("sleep_score") for r in wk])
        avg_steps = _avg([r.get("steps") for r in wk])
        sum_ex = sum(r.get("exercise_minutes") or 0 for r in wk)
        ex_rate = min(100, round(sum_ex / (ex_goal * 7) * 100)) if ex_goal else 0
        avg_rhr = _avg([r.get("heart_rate_rest") for r in wk]) or 60
        score = round(0.45 * (avg_sleep or 70) + 0.30 * ex_rate
                      + 0.25 * max(0, min(100, 100 - (avg_rhr - 50) * 2)))
        return {"workout_days": workout_days, "total_burn": total_burn,
                "avg_sleep": avg_sleep, "avg_steps": avg_steps, "ex_rate": ex_rate, "score": score}

    tw, lw = _week_stats(this_week), _week_stats(last_week)

    weight = profile.get("weight_kg")
    bmi = tools.calc_bmi(weight, profile.get("height_cm", 175)) if weight else None
    bmr = tools.calc_bmr(weight, profile.get("height_cm", 175),
                         profile.get("age", 30), profile.get("gender", "male")) if weight else None

    # 最新营养
    nut = _query_one(
        "SELECT nutrition_result, balance_score FROM nutrition_logs "
        "WHERE user_id = %s ORDER BY date DESC LIMIT 1", (user_id,))
    nr = (nut or {}).get("nutrition_result") or {}
    total_cal = nr.get("total_calories")
    p, c, f = nr.get("protein_g"), nr.get("carbs_g"), nr.get("fat_g")
    macro_cal = (p or 0) * 4 + (c or 0) * 4 + (f or 0) * 9
    ratios = ({"protein": round((p or 0) * 4 / macro_cal * 100), "carbs": round((c or 0) * 4 / macro_cal * 100),
               "fat": round((f or 0) * 9 / macro_cal * 100)} if macro_cal else {})

    score = tw["score"]
    status = "活力充沛" if (score or 0) >= 80 else ("状态平稳" if (score or 0) >= 60 else "需要恢复")
    risk = "低风险" if (score or 0) >= 75 else ("中风险" if (score or 0) >= 55 else "偏高风险")

    return {
        "kpi": {
            "health_score": score,
            "score_delta_vs_last_week": (score - lw["score"]) if (score is not None and lw["score"] is not None) else None,
            "status": status,
            "exercise_rate": tw["ex_rate"],
            "exercise_rate_delta": tw["ex_rate"] - lw["ex_rate"] if last_week else None,
            "risk": risk,
        },
        "body_overview": {
            "heart_rate": latest.get("heart_rate_avg") or latest.get("heart_rate_rest"),
            "weight_kg": weight, "bmi": bmi, "bmr": bmr,
            "body_fat_pct": profile.get("body_fat_pct"),
            "muscle_mass_kg": profile.get("muscle_mass_kg"),
            "update_date": str(latest.get("date")) if latest else None,
        },
        "sleep": {
            "score": sleep.get("sleep_score"), "total_hours": sleep.get("total_hours"),
            "deep_sleep_percent": sleep.get("deep_sleep_percent"),
            "rem_sleep_percent": sleep.get("rem_sleep_percent"),
            "stages_timeline": sleep.get("stages_timeline", []),
        },
        "nutrition": {
            "total_calories": total_cal, "protein_g": p, "carbs_g": c, "fat_g": f,
            "ratios": ratios, "balance_score": (nut or {}).get("balance_score"),
        },
        "exercise_today": {
            "steps": latest.get("steps"), "steps_goal": steps_goal,
            "duration_minutes": latest.get("exercise_minutes"),
            "calories_burned": latest.get("calories_burned"),
            "intensity": "高" if (latest.get("exercise_minutes") or 0) >= 60 else
                         ("中等" if (latest.get("exercise_minutes") or 0) >= 25 else "低"),
        },
        "week_summary": {
            "workout_days": tw["workout_days"], "days_goal": goals.get("exercise_days_goal", 7),
            "total_calories_burned": tw["total_burn"],
            "avg_steps": tw["avg_steps"], "avg_sleep": tw["avg_sleep"],
        },
        "goals": goals,
    }
