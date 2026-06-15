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

    # --- 运动负荷：exercise_records（结构化列优先，回退 analysis_result）---
    ex_row = _query_one(
        "SELECT actual_duration_min, peak_hr, hr_60s_after, actual_rpe, "
        "calories_burned, analysis_result FROM exercise_records "
        "WHERE user_id = %s ORDER BY date DESC LIMIT 1",
        (user_id,),
    )
    ex_data = (ex_row or {}).get("analysis_result") or {}
    if ex_row:
        exercise = {
            "duration_minutes": _pick(ex_row.get("actual_duration_min"), ex_data.get("duration_minutes"),
                                       scen["exercise"]["duration_minutes"]),
            "peak_hr": _pick(ex_row.get("peak_hr"), ex_data.get("peak_hr"),
                              scen["exercise"]["peak_hr"]),
            "hr_60s": _pick(ex_row.get("hr_60s_after"), ex_data.get("hr_60s"),
                             scen["exercise"]["hr_60s"]),
            "rpe": _pick(ex_row.get("actual_rpe"), ex_data.get("rpe"),
                          scen["exercise"]["rpe"]),
        }
        sources["exercise"] = "db"
    else:
        exercise = dict(scen["exercise"])
        sources["exercise"] = "mock"

    # --- 饮食描述：nutrition_logs(recognized_foods/nutrition_result JSONB) ---
    nut_row = _query_one(
        "SELECT recognized_foods, nutrition_result, total_calories_actual, "
        "narrative FROM nutrition_logs "
        "WHERE user_id = %s ORDER BY date DESC LIMIT 1",
        (user_id,),
    )
    diet_narrative = None
    if nut_row:
        # 优先取 narrative 结构化列，回退 nutrition_result.diet_narrative / recognized_foods
        nr = nut_row.get("nutrition_result") or {}
        rf = nut_row.get("recognized_foods")
        narrative_col = nut_row.get("narrative")
        diet_narrative = narrative_col or nr.get("diet_narrative") if isinstance(nr, dict) else None
        if not diet_narrative and rf:
            diet_narrative = "，".join(map(str, rf)) if isinstance(rf, list) else str(rf)
    if diet_narrative:
        sources["diet"] = "db"
    else:
        diet_narrative = scen["diet"]["diet_narrative"]
        sources["diet"] = "mock"

    # --- 身体测量：users.weight_kg；body_fat_pct 现已接入结构化列 ---
    profile = get_user_profile(user_id)
    weight_kg = profile.get("weight_kg") or scen["body"]["weight_kg"]
    body_fat_pct = profile.get("body_fat_pct") or scen["body"]["body_fat_pct"]
    # body 来源以体重/体脂的真实来源为准
    src_body = profile.get("_source", "mock")
    sources["body"] = src_body if profile.get("weight_kg") else "mock"

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


# =============================================================================
# 四、三页通用工具（「运动分析 / 睡眠监测 / 饮食管理」共用）
# =============================================================================

def _mark(sources: Dict[str, str], field: str, src: str) -> None:
    """在 sources 字典内标记某字段来源（db / mock / derived / default）。"""
    sources[field] = src


def _pick(col_val, jsonb_get, default=None):
    """回退助手：优先结构化列，缺失回退旧 JSONB 镜像同义键，再无则用 default。"""
    if col_val is not None:
        return col_val
    if jsonb_get is not None:
        return jsonb_get
    return default


def _get_goals(profile: Dict[str, Any]) -> Dict[str, Any]:
    """从 users.goals 读取目标，缺省用设计图常量。

    返回值与 get_week_overview 内的 _goal 读取共享语义。
    """
    goals = profile.get("goals") or {}
    return {
        "steps_goal": goals.get("steps_goal", 10000),
        "exercise_minutes_goal": goals.get("exercise_minutes_goal", 60),
        "calorie_intake_target": goals.get("calorie_intake_target", 2000),
        "calorie_burn_target": goals.get("calorie_burn_target", 500),
        "sleep_recommend_min": goals.get("sleep_recommend_min", 7),
        "sleep_recommend_max": goals.get("sleep_recommend_max", 9),
        "nap_recommend_min": goals.get("nap_recommend_min", 20),
        "nap_recommend_max": goals.get("nap_recommend_max", 30),
    }


def _get_watch_sequence(user_id: int, days: int = 7) -> List[Dict[str, Any]]:
    """获取近 N 天 watch_data 序列，用于睡眠趋势 / 步数趋势等聚合。"""
    return _query_all(
        "SELECT date, steps, exercise_minutes, calories_burned, "
        "heart_rate_avg, heart_rate_rest, hrv_data, sleep_data "
        "FROM watch_data WHERE user_id = %s "
        "ORDER BY date DESC LIMIT %s",
        (user_id, days),
    )


def _execute_write(sql: str, params: tuple) -> bool:
    """执行 UPDATE / INSERT 并提交，返回是否成功。"""
    try:
        from store.db import get_pool
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)
    except Exception as e:
        logger.debug("[health_data] DB 写入失败: %s", e)
        return False


# =============================================================================
# 五、三页聚合函数
# =============================================================================

# -------- mock 默认值 --------
_MOCK_SLEEP_TODAY = {
    "sleep_score": 75, "total_hours": 7.0, "deep_sleep_percent": 20,
    "nap_minutes": 20, "bedtime": "23:00", "wake_time": "06:30",
}
_MOCK_SLEEP_ADVICE = {
    "sleep": "建议保持规律作息，每天在同一时间入睡和起床。睡前一小时避免使用电子设备。",
    "nutrition": "晚餐避免高脂高糖食物，可选择富含色氨酸的食物如香蕉、燕麦、温牛奶，有助于促进睡眠。",
    "exercise": "下午进行中等强度有氧运动有助于加深夜间睡眠，但睡前2小时内避免剧烈运动。",
}
_MOCK_EXERCISE_ADVICE = {
    "exercise": "今日建议进行中等强度有氧运动30-45分钟，保持心率在最大心率的60-70%区间。运动后充分拉伸。",
    "nutrition": "运动后30分钟内补充蛋白质和碳水，比例建议1:3。多喝水补充电解质。",
    "sleep": "确保今晚睡眠质量以促进肌肉恢复和生长激素分泌，建议睡眠7-9小时。",
}
_MOCK_NUTRITION_EXERCISE_ADVICE = {
    "training_type": "有氧训练",
    "duration": "40-60分钟",
    "calorie_target": 400,
    "exercises": [
        {"name": "慢跑", "duration": "20分钟"},
        {"name": "动感单车", "duration": "20分钟"},
        {"name": "核心训练", "sets": 3, "reps": 12},
    ],
}


def _grade_sleep(score: Optional[float]) -> str:
    """睡眠评分 → 等级（derived）。"""
    if score is None:
        return "暂无"
    if score >= 85:
        return "优秀"
    if score >= 70:
        return "良好"
    if score >= 50:
        return "一般"
    return "较差"


def _status_range(value: Optional[float], lo: float, hi: float,
                   labels: tuple = ("不足", "达标", "超标")) -> str:
    """通用达标/区间判定（derived）。"""
    if value is None:
        return "暂无数据"
    if value < lo:
        return labels[0]
    if value <= hi:
        return labels[1]
    return labels[2]


# -------- 2. 睡眠监测 --------
def get_sleep_overview(user_id: int, range_days: int = 7) -> Dict[str, Any]:
    """聚合睡眠监测页全部数据（v3.1 结构化列 + sleep_log + user_plans）。

    Returns:
        {today: {sleep_score, grade, total_hours, deep_sleep_hours,
                 nap_minutes, bedtime, wake_time},
         duration: {status, recommend_min, recommend_max},
         nap: {status, recommend_min, recommend_max},
         trend: [{date, total_hours, sleep_score}],
         advice: {sleep, nutrition, exercise},
         foods: {recommended, avoid}}
    """
    profile = get_user_profile(user_id)
    goals = _get_goals(profile)
    raw_goals = profile.get("goals") or {}
    sources: Dict[str, str] = {}

    # --- 优先 sleep_log 取 bedtime/wake_time，回退 watch_data ---
    sleep_log = _query_one(
        "SELECT bedtime_at, wake_time_at FROM sleep_log "
        "WHERE user_id = %s ORDER BY sleep_date DESC LIMIT 1",
        (user_id,),
    )

    # --- 取最新 watch_data 结构化列（回退 JSONB）---
    today_row = _query_one(
        "SELECT sleep_score, total_sleep_min, deep_sleep_min, nap_min, "
        "actual_bedtime, actual_wake_time, sleep_data "
        "FROM watch_data "
        "WHERE user_id = %s ORDER BY date DESC LIMIT 1",
        (user_id,),
    )
    sd = (today_row.get("sleep_data") or {}) if today_row else {}
    has_db = today_row is not None

    if has_db:
        # 结构化列优先，回退 JSONB 镜像同义键
        sleep_score = _pick(today_row.get("sleep_score"), sd.get("sleep_score"))
        # P1: total_sleep_min 是分钟(÷60→小时), sleep_data.total_hours 已经是小时, 不可混入同一变量
        tsm = today_row.get("total_sleep_min")
        sd_hours = sd.get("total_hours")
        if tsm is not None:
            total_hours = round(tsm / 60, 1)
        elif sd_hours is not None:
            total_hours = sd_hours
        else:
            total_hours = None
        # deep_sleep: deep_sleep_min/60, 回退 deep_sleep_percent × total_hours
        dsm = today_row.get("deep_sleep_min")
        sd_deep_min = sd.get("deep_sleep_min")
        deep_sleep_pct = sd.get("deep_sleep_percent")
        if dsm is not None:
            deep_sleep_hours = round(dsm / 60, 1)
        elif sd_deep_min is not None:
            deep_sleep_hours = round(sd_deep_min / 60, 1)
        elif deep_sleep_pct is not None and total_hours is not None:
            deep_sleep_hours = round(deep_sleep_pct / 100 * total_hours, 1)
        else:
            deep_sleep_hours = None
        nap_minutes = _pick(today_row.get("nap_min"), sd.get("nap_minutes"))
        # bedtime/wake: sleep_log > watch_data 结构化列 > JSONB 镜像
        if sleep_log:
            bed_dt = sleep_log.get("bedtime_at")
            wake_dt = sleep_log.get("wake_time_at")
            bedtime = bed_dt.strftime("%H:%M") if hasattr(bed_dt, 'strftime') else str(bed_dt)[:5] if bed_dt else None
            wake_time = wake_dt.strftime("%H:%M") if hasattr(wake_dt, 'strftime') else str(wake_dt)[:5] if wake_dt else None
        else:
            bedtime = _pick(today_row.get("actual_bedtime"), sd.get("bedtime"))
            wake_time = _pick(today_row.get("actual_wake_time"), sd.get("wake_time"))

        _mark(sources, "sleep_score", "db")
        _mark(sources, "total_hours", "db")
        _mark(sources, "deep_sleep_hours", "derived")
        _mark(sources, "nap_minutes", "db" if nap_minutes is not None else "mock")
        _mark(sources, "bedtime", "db")
        _mark(sources, "wake_time", "db")
    else:
        sleep_score = _MOCK_SLEEP_TODAY["sleep_score"]
        total_hours = _MOCK_SLEEP_TODAY["total_hours"]
        deep_sleep_hours = _MOCK_SLEEP_TODAY["deep_sleep_percent"] / 100 * total_hours if total_hours else None
        nap_minutes = _MOCK_SLEEP_TODAY["nap_minutes"]
        bedtime = _MOCK_SLEEP_TODAY["bedtime"]
        wake_time = _MOCK_SLEEP_TODAY["wake_time"]
        _mark(sources, "sleep_score", "mock")
        _mark(sources, "total_hours", "mock")
        _mark(sources, "deep_sleep_hours", "derived")
        _mark(sources, "nap_minutes", "mock")
        _mark(sources, "bedtime", "mock")
        _mark(sources, "wake_time", "mock")

    grade = _grade_sleep(sleep_score)
    _mark(sources, "grade", "derived")

    d_lo, d_hi = goals["sleep_recommend_min"], goals["sleep_recommend_max"]
    n_lo, n_hi = goals["nap_recommend_min"], goals["nap_recommend_max"]
    duration_status = _status_range(total_hours, d_lo, d_hi)
    nap_status = _status_range(nap_minutes, n_lo, n_hi)
    _mark(sources, "duration.status", "derived")
    _mark(sources, "nap.status", "derived")
    _mark(sources, "duration.recommend_min", "db" if raw_goals.get("sleep_recommend_min") else "default")
    _mark(sources, "duration.recommend_max", "db" if raw_goals.get("sleep_recommend_max") else "default")
    _mark(sources, "nap.recommend_min", "db" if raw_goals.get("nap_recommend_min") else "default")
    _mark(sources, "nap.recommend_max", "db" if raw_goals.get("nap_recommend_max") else "default")

    # --- trend（从 watch_data 历史取结构化列 / JSONB）---
    rows = _get_watch_sequence(user_id, range_days)
    trend = []
    for r in reversed(rows):
        s = r.get("sleep_data") or {}
        sc = _pick(r.get("sleep_score"), s.get("sleep_score"))
        th_raw = s.get("total_hours")
        tsm = r.get("total_sleep_min")
        th = round(tsm / 60, 1) if tsm else th_raw
        if sc is not None or th is not None:
            trend.append({"date": str(r["date"]), "total_hours": th, "sleep_score": sc})
    _mark(sources, "trend", "db" if trend else "mock")

    # --- advice: user_plans → 规则兜底 ---
    plan = _query_one(
        "SELECT sleep_plan, training_plan FROM user_plans "
        "WHERE user_id = %s ORDER BY plan_date DESC LIMIT 1",
        (user_id,),
    )
    if plan:
        sp = plan.get("sleep_plan") or {}
        tp = plan.get("training_plan") or {}
        suggestions = sp.get("suggestions") or []
        sleep_advice = "；".join(s.get("title", "") for s in suggestions) if suggestions else _MOCK_SLEEP_ADVICE["sleep"]
        exercise_advice = tp.get("reason") or _MOCK_SLEEP_ADVICE["exercise"]
        _mark(sources, "advice.sleep", "derived" if suggestions else "default")
        _mark(sources, "advice.nutrition", "default")
        _mark(sources, "advice.exercise", "derived" if tp.get("reason") else "default")
    else:
        sleep_advice = _MOCK_SLEEP_ADVICE["sleep"]
        exercise_advice = _MOCK_SLEEP_ADVICE["exercise"]
        _mark(sources, "advice.sleep", "mock")
        _mark(sources, "advice.nutrition", "mock")
        _mark(sources, "advice.exercise", "mock")
    nutrition_advice = "晚餐避免高脂高糖食物，可选择富含色氨酸的食物如香蕉、燕麦、温牛奶，有助于促进睡眠。"

    # --- foods: curated 常量（对齐前端图标集），标 default ---
    _CURATED_RECOMMENDED = ["香蕉", "燕麦", "牛奶", "鸡蛋", "坚果"]
    _CURATED_AVOID = ["咖啡", "辛辣食物", "油炸食品", "甜点", "奶茶"]
    _mark(sources, "foods.recommended", "default")
    _mark(sources, "foods.avoid", "default")

    return {
        "user_id": user_id,
        "sleep": {
            "today": {
                "sleep_score": sleep_score,
                "grade": grade,
                "total_hours": total_hours,
                "deep_sleep_hours": deep_sleep_hours,
                "nap_minutes": nap_minutes,
                "bedtime": bedtime,
                "wake_time": wake_time,
            },
            "duration": {"status": duration_status, "recommend_min": d_lo, "recommend_max": d_hi},
            "nap": {"status": nap_status, "recommend_min": n_lo, "recommend_max": n_hi},
            "trend": trend,
            "advice": {
                "sleep": sleep_advice,
                "nutrition": nutrition_advice,
                "exercise": exercise_advice,
            },
            "foods": {"recommended": list(_CURATED_RECOMMENDED), "avoid": list(_CURATED_AVOID)},
        },
        "sources": sources,
    }


def save_sleep_entry(uid: int, bedtime: str, wake_time: str,
                     nap_minutes: Optional[int] = None,
                     on_date: Optional[str] = None) -> Dict[str, Any]:
    """写入一条睡眠记录（真值源：sleep_log，回灌 watch_data）。

    Args:
        uid: 用户 ID
        bedtime: ISO 格式入睡时间，如 "2026-06-01T23:20"
        wake_time: ISO 格式起床时间，如 "2026-06-02T07:20"
        nap_minutes: 可选小憩分钟数
        on_date: 睡眠日期字符串 YYYY-MM-DD，默认今天（起床日）

    Returns:
        {"saved": bool, "sleep_data": {...}}

    Raises:
        ValueError: bedtime 或 wake_time 不是合法 ISO 时间字符串；
            或起床时间不晚于入睡时间
    """
    import json
    from datetime import datetime

    on_date = on_date or datetime.now().strftime("%Y-%m-%d")
    b = datetime.fromisoformat(bedtime)
    w = datetime.fromisoformat(wake_time)
    if w <= b:
        raise ValueError(f"起床时间 ({wake_time}) 必须晚于入睡时间 ({bedtime})")
    total_hours = round((w - b).total_seconds() / 3600, 1)
    sleep_date = on_date  # sleep_log 的 sleep_date = 起床日

    # 1) sleep_log upsert（真值源）
    log_ok = _execute_write(
        """INSERT INTO sleep_log (user_id, sleep_date, bedtime_at, wake_time_at, source)
           VALUES (%s, %s, %s, %s, 'user_input')
           ON CONFLICT (user_id, sleep_date) DO UPDATE SET
               bedtime_at=EXCLUDED.bedtime_at, wake_time_at=EXCLUDED.wake_time_at,
               updated_at=CURRENT_TIMESTAMP""",
        (uid, sleep_date, b, w),
    )
    if not log_ok:
        return {"saved": False, "sleep_data": {}}

    # 2) 回灌 watch_data（actual_bedtime/actual_wake_time/nap_min + sleep_data 镜像）
    sleep_data = {
        "bedtime": bedtime,
        "wake_time": wake_time,
        "total_hours": total_hours,
    }
    if nap_minutes is not None:
        sleep_data["nap_minutes"] = nap_minutes
    actual_bed = b.strftime("%H:%M")
    actual_wake = w.strftime("%H:%M")
    total_sleep_min = int(round((w - b).total_seconds() / 60))

    existing = _query_one(
        "SELECT id FROM watch_data WHERE user_id = %s AND date = %s",
        (uid, sleep_date),
    )
    if existing:
        _execute_write(
            """UPDATE watch_data SET
                actual_bedtime=%s, actual_wake_time=%s,
                total_sleep_min=COALESCE(total_sleep_min, %s),
                nap_min=COALESCE(nap_min, %s),
                sleep_data = COALESCE(sleep_data, '{}'::jsonb) || %s::jsonb
               WHERE id=%s""",
            (actual_bed, actual_wake, total_sleep_min, nap_minutes or 0,
             json.dumps(sleep_data), existing["id"]),
        )
    else:
        _execute_write(
            """INSERT INTO watch_data (user_id, date, actual_bedtime, actual_wake_time,
                total_sleep_min, nap_min, sleep_data)
               VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)""",
            (uid, sleep_date, actual_bed, actual_wake, total_sleep_min,
             nap_minutes or 0, json.dumps(sleep_data)),
        )
    return {"saved": True, "sleep_data": sleep_data}


# -------- 3. 运动分析 --------
def get_exercise_overview(user_id: int) -> Dict[str, Any]:
    """聚合运动分析页全部数据（v3.1 结构化列 + user_plans + 跨用户聚合）。

    Returns:
        {today_overview: {steps, calories_burned, duration_minutes, intensity, goals},
         today_status: {diet, sleep, fatigue},
         today_records: [{exercise_type, duration_minutes, calories, ...}],
         week_trend: [{date, steps}],
         advice: {exercise, nutrition, sleep},
         achievement: {percentile, description}}
    """
    from datetime import date

    profile = get_user_profile(user_id)
    goals = _get_goals(profile)
    raw_goals = profile.get("goals") or {}
    sources: Dict[str, str] = {}
    today_str = date.today().isoformat()

    # --- 最新 watch_data ---
    today_row = _query_one(
        "SELECT date, steps, exercise_minutes, calories_burned, "
        "heart_rate_avg, heart_rate_rest, hrv_data, sleep_data, sleep_score, total_sleep_min "
        "FROM watch_data WHERE user_id = %s ORDER BY date DESC LIMIT 1",
        (user_id,),
    )
    has_wear = today_row is not None

    if has_wear:
        steps = today_row.get("steps") or 0
        calories_burned = today_row.get("calories_burned") or 0
        duration_minutes = today_row.get("exercise_minutes") or 0
        _mark(sources, "steps", "db")
        _mark(sources, "calories_burned", "db")
        _mark(sources, "duration_minutes", "db")
    else:
        steps = 8560
        calories_burned = 380
        duration_minutes = 45
        _mark(sources, "steps", "mock")
        _mark(sources, "calories_burned", "mock")
        _mark(sources, "duration_minutes", "mock")

    # intensity (derived, same rule as get_week_overview)
    intensity = "高" if duration_minutes >= 60 else ("中等" if duration_minutes >= 25 else "低")
    _mark(sources, "intensity", "derived")

    steps_goal = goals["steps_goal"]
    duration_goal = goals["exercise_minutes_goal"]
    calories_goal = goals["calorie_burn_target"]
    _mark(sources, "steps_goal", "db" if raw_goals.get("steps_goal") else "default")
    _mark(sources, "duration_goal", "db" if raw_goals.get("exercise_minutes_goal") else "default")
    _mark(sources, "calories_goal", "db" if raw_goals.get("calorie_burn_target") else "default")

    # --- today_status ---
    # 饮食情况
    nut_row_today = _query_one(
        "SELECT total_calories_actual, nutrition_result FROM nutrition_logs "
        "WHERE user_id = %s AND date = %s",
        (user_id, today_str),
    )
    if nut_row_today:
        intake_cal = _pick(nut_row_today.get("total_calories_actual"),
                           (nut_row_today.get("nutrition_result") or {}).get("total_calories"), 0)
    else:
        intake_cal = 0
    diet_status = "良好" if intake_cal >= goals["calorie_intake_target"] * 0.8 else "偏低"
    _mark(sources, "diet.status", "db" if nut_row_today else "mock")
    _mark(sources, "diet.intake", "db" if nut_row_today else "mock")

    # 睡眠情况
    sd_today = (today_row.get("sleep_data") or {}) if today_row else {}
    if today_row:
        sleep_score_today = _pick(today_row.get("sleep_score"), sd_today.get("sleep_score"))
        sleep_hours_raw = today_row.get("total_sleep_min")
        sleep_hours = round(sleep_hours_raw / 60, 1) if sleep_hours_raw else sd_today.get("total_hours", 7.0)
    else:
        sleep_score_today = None
        sleep_hours = 7.0
    sleep_status = "良好" if (sleep_score_today or 0) >= 70 else ("一般" if (sleep_score_today or 0) >= 50 else "较差")
    _mark(sources, "sleep.status", "db" if (today_row and sd_today) else "mock")
    _mark(sources, "sleep.hours", "db" if (today_row and sd_today) else "mock")

    # 疲劳度 (derived from compute_metrics)
    try:
        metrics = compute_metrics(user_id)
        fatigue_level = metrics["derived"]["fatigue"]
        fatigue_advice = {
            "low": "疲劳程度低，状态良好，可进行常规训练。",
            "medium": "轻度疲劳，建议降低训练强度，优先恢复。",
            "high": "疲劳程度较高，建议休息或进行低强度恢复训练。",
        }.get(fatigue_level, "状态正常。")
    except Exception:
        fatigue_level = "low"
        fatigue_advice = "状态正常。"
    _mark(sources, "fatigue.level", "derived")
    _mark(sources, "fatigue.advice", "derived")

    # --- today_records（结构化列优先，回退 analysis_result；start/end/distance_km 现已可查 db）---
    today_records_db = _query_all(
        "SELECT exercise_type, actual_duration_min, calories_burned, "
        "start_time, end_time, distance_km, analysis_result "
        "FROM exercise_records "
        "WHERE user_id = %s AND date = %s ORDER BY id",
        (user_id, today_str),
    )
    today_records = []
    for idx, er in enumerate(today_records_db):
        ar = er.get("analysis_result") or {}
        dur = _pick(er.get("actual_duration_min"), ar.get("duration_minutes"), 30)
        cal = _pick(er.get("calories_burned"), ar.get("calories"), 200)
        st = er.get("start_time")
        et = er.get("end_time")
        dst = er.get("distance_km")
        # 拼接 time_range
        if st and et:
            st_s = st.strftime("%H:%M") if hasattr(st, 'strftime') else str(st)[:5]
            et_s = et.strftime("%H:%M") if hasattr(et, 'strftime') else str(et)[:5]
            time_range = f"{st_s}-{et_s}"
        else:
            time_range = ar.get("time_range", "07:00-07:30")
            _mark(sources, f"records.{idx+1}.time_range", "mock")
        # distance_km
        if dst is not None:
            distance_km = float(dst) if not isinstance(dst, (float, int)) else dst
            _mark(sources, f"records.{idx+1}.distance_km", "db")
        else:
            distance_km = ar.get("distance_km", 3.0)
            _mark(sources, f"records.{idx+1}.distance_km", "mock")

        record = {
            "exercise_type": er.get("exercise_type") or ar.get("exercise_type", "未知运动"),
            "duration_minutes": dur,
            "calories": cal,
            "time_range": time_range,
            "distance_km": distance_km,
        }
        today_records.append(record)
        _mark(sources, f"records.{idx+1}.exercise_type", "db")
        _mark(sources, f"records.{idx+1}.duration_minutes", "db")
        _mark(sources, f"records.{idx+1}.calories", "db")
    if not today_records:
        _mark(sources, "today_records", "db")

    # --- week_trend ---
    week_rows = _get_watch_sequence(user_id, 7)
    week_trend = [
        {"date": str(r["date"]), "steps": r.get("steps") or 0}
        for r in reversed(week_rows)
    ]
    _mark(sources, "week_trend", "db" if week_trend else "mock")

    # --- advice: user_plans → 规则兜底 ---
    plan = _query_one(
        "SELECT training_plan, sleep_plan, diet_plan FROM user_plans "
        "WHERE user_id = %s ORDER BY plan_date DESC LIMIT 1",
        (user_id,),
    )
    if plan:
        tp = plan.get("training_plan") or {}
        sp = plan.get("sleep_plan") or {}
        dp = plan.get("diet_plan") or {}
        ex_adv = tp.get("reason") or _MOCK_EXERCISE_ADVICE["exercise"]
        sleep_adv = "；".join(s.get("title", "") for s in (sp.get("suggestions") or [])) if sp.get("suggestions") else _MOCK_EXERCISE_ADVICE["sleep"]
        nut_adv = dp.get("notes") or _MOCK_EXERCISE_ADVICE["nutrition"]
        _mark(sources, "advice.exercise", "derived" if tp.get("reason") else "default")
        _mark(sources, "advice.sleep", "derived" if sp.get("suggestions") else "default")
        _mark(sources, "advice.nutrition", "derived" if dp.get("notes") else "default")
    else:
        ex_adv = _MOCK_EXERCISE_ADVICE["exercise"]
        sleep_adv = _MOCK_EXERCISE_ADVICE["sleep"]
        nut_adv = _MOCK_EXERCISE_ADVICE["nutrition"]
        _mark(sources, "advice.exercise", "mock")
        _mark(sources, "advice.sleep", "mock")
        _mark(sources, "advice.nutrition", "mock")

    # --- achievement.percentile: 跨用户 health_score 排名聚合（derived）---
    percentile = None
    try:
        # sleep_score 列优先，回退 sleep_data->>'sleep_score' JSONB（seed 未填列）
        _SS = "coalesce(w.sleep_score, (w.sleep_data->>'sleep_score')::int)"
        all_scores = _query_all(
            f"SELECT w3.hs FROM ("
            "  SELECT w2.user_id,"
            "    round(0.45 * coalesce(w2.avg_ss,70) + 0.30 * w2.ex_r + 0.25 * w2.rhr_s) AS hs"
            "  FROM ("
            "    SELECT w.user_id,"
            f"      avg({_SS}) AS avg_ss,"
            "      least(100::float, round(coalesce(sum(w.exercise_minutes),0) / (60.0*7) * 100)) AS ex_r,"
            "      greatest(0::float, least(100::float, 100 - (coalesce(avg(w.heart_rate_rest),60) - 50) * 2)) AS rhr_s"
            "    FROM watch_data w WHERE w.date >= CURRENT_DATE - 7"
            "    GROUP BY w.user_id"
            "  ) w2"
            ") w3 ORDER BY w3.hs DESC", ()
        )
        if all_scores:
            scores = [s["hs"] for s in all_scores if s.get("hs") is not None]
            my_score_raw = _query_one(
                f"SELECT 0.45 * coalesce(avg({_SS}),70)"
                " + 0.30 * least(100::float, round(coalesce(sum(w.exercise_minutes),0) / (60.0*7)*100))"
                " + 0.25 * greatest(0::float, least(100::float, 100 - (coalesce(avg(w.heart_rate_rest),60)-50)*2)) AS hs"
                " FROM watch_data w WHERE w.user_id=%s AND w.date >= CURRENT_DATE-7",
                (user_id,),
            )
            my_score = (my_score_raw or {}).get("hs")
            if my_score is not None and scores:
                rank = sum(1 for s in scores if s > my_score) + 1
                percentile = int(round((len(scores) - rank + 1) / len(scores) * 100))
    except Exception:
        pass
    if percentile is not None:
        _mark(sources, "achievement.percentile", "derived")
    else:
        percentile = 75
        _mark(sources, "achievement.percentile", "mock")
    _mark(sources, "achievement.description", "mock")

    return {
        "user_id": user_id,
        "exercise": {
            "today_overview": {
                "steps": steps,
                "calories_burned": calories_burned,
                "duration_minutes": duration_minutes,
                "intensity": intensity,
                "steps_goal": steps_goal,
                "duration_goal": duration_goal,
                "calories_goal": calories_goal,
            },
            "today_status": {
                "diet": {"status": diet_status, "intake": intake_cal,
                         "goal": goals["calorie_intake_target"]},
                "sleep": {"status": sleep_status, "hours": sleep_hours},
                "fatigue": {"level": fatigue_level, "advice": fatigue_advice},
            },
            "today_records": today_records,
            "week_trend": week_trend,
            "advice": {"exercise": ex_adv, "nutrition": nut_adv, "sleep": sleep_adv},
            "achievement": {
                "percentile": percentile,
                "description": f"超越了{percentile}%的同龄健康用户",
            },
        },
        "sources": sources,
    }


# -------- 4. 饮食管理 --------
def get_nutrition_overview(user_id: int, on_date: Optional[str] = None) -> Dict[str, Any]:
    """聚合饮食管理页全部数据（v3.1 结构化列 + recognized_foods + user_plans）。

    Args:
        user_id: 用户 ID
        on_date: 日期 YYYY-MM-DD，默认今天

    Returns:
        {kpi, energy, meals, exercise_advice}
    """
    from datetime import date
    from agents import health_tools as tools

    on_date = on_date or date.today().isoformat()
    profile = get_user_profile(user_id)
    goals = _get_goals(profile)
    sources: Dict[str, str] = {}

    # --- 当日 nutrition_logs（结构化列优先，回退 JSONB）---
    nut_row = _query_one(
        "SELECT total_calories_actual, calories_remaining, protein_g, carbs_g, fat_g, "
        "balance_score, recognized_foods, meal_breakdown, nutrition_result "
        "FROM nutrition_logs WHERE user_id = %s AND date = %s",
        (user_id, on_date),
    )
    nr = (nut_row.get("nutrition_result") or {}) if nut_row else {}
    has_nut = nut_row is not None

    if has_nut:
        intake_calories = _pick(nut_row.get("total_calories_actual"), nr.get("total_calories"), 0)
        protein_g = _pick(nut_row.get("protein_g"), nr.get("protein_g"), 0)
        carbs_g = _pick(nut_row.get("carbs_g"), nr.get("carbs_g"), 0)
        fat_g = _pick(nut_row.get("fat_g"), nr.get("fat_g"), 0)
        # remaining: 如果有结构化列 calories_remaining 则取，否则派生
        calories_remaining_col = nut_row.get("calories_remaining")
    else:
        intake_calories = 0
        protein_g = carbs_g = fat_g = 0
        calories_remaining_col = None

    goal_cal = goals["calorie_intake_target"]

    # --- kpi ---
    if has_nut and calories_remaining_col is not None:
        remaining_calories = calories_remaining_col
        _mark(sources, "kpi.remaining_calories", "db")
    else:
        remaining_calories = max(0, goal_cal - (intake_calories or 0))
        _mark(sources, "kpi.remaining_calories", "derived")
    achievement_rate = round((intake_calories or 0) / goal_cal * 100, 1) if goal_cal else 0
    _mark(sources, "kpi.goal_calories", "db")
    _mark(sources, "kpi.intake_calories", "db" if has_nut else "mock")
    _mark(sources, "kpi.achievement_rate", "derived")

    # --- energy ---
    macro_cal = (protein_g or 0) * 4 + (carbs_g or 0) * 4 + (fat_g or 0) * 9
    if macro_cal > 0:
        carbs_pct = round((carbs_g or 0) * 4 / macro_cal * 100)
        protein_pct = round((protein_g or 0) * 4 / macro_cal * 100)
        fat_pct = round((fat_g or 0) * 9 / macro_cal * 100)
    else:
        carbs_pct = protein_pct = fat_pct = 0

    macros = {
        "carbs": {"grams": carbs_g or 0, "calories": (carbs_g or 0) * 4, "percent": carbs_pct},
        "protein": {"grams": protein_g or 0, "calories": (protein_g or 0) * 4, "percent": protein_pct},
        "fat": {"grams": fat_g or 0, "calories": (fat_g or 0) * 9, "percent": fat_pct},
    }
    _mark(sources, "energy.total_calories", "db" if has_nut else "mock")
    _mark(sources, "energy.macros.*.grams", "db" if has_nut else "mock")
    _mark(sources, "energy.macros.*.calories", "db" if has_nut else "mock")
    _mark(sources, "energy.macros.*.percent", "derived")

    # BMR (derived)
    try:
        bmr_val = tools.calc_bmr(
            profile.get("weight_kg", 80),
            profile.get("height_cm", 175),
            profile.get("age", 30),
            profile.get("gender", "male"),
        )
    except Exception:
        bmr_val = 1678
    _mark(sources, "energy.bmr", "derived")

    # exercise_burn from watch_data
    burn_row = _query_one(
        "SELECT calories_burned FROM watch_data "
        "WHERE user_id = %s AND date = %s",
        (user_id, on_date),
    )
    exercise_burn = (burn_row or {}).get("calories_burned") or 0
    _mark(sources, "energy.exercise_burn", "db" if burn_row else "mock")

    recommended_calories = goal_cal
    _mark(sources, "energy.recommended_calories", "db")

    # energy_gap = 目标 − 已摄入（可为负）
    energy_gap = goal_cal - (intake_calories or 0)
    _mark(sources, "energy.energy_gap", "derived")

    # --- meals: recognized_foods + meal_breakdown（结构化）---
    recognized = (nut_row.get("recognized_foods") or []) if has_nut else []
    breakdown = (nut_row.get("meal_breakdown") or []) if has_nut else None
    if recognized and breakdown:
        # 以 meal_breakdown 为骨架，recognized_foods 按 meal 分组挂 foods
        bd_map = {b["meal"]: b for b in breakdown if isinstance(b, dict)}
        meals = []
        for b in breakdown if isinstance(breakdown, list) else breakdown:
            if not isinstance(b, dict):
                continue
            meal_name = b.get("meal", "")
            meal_time = b.get("time", "12:00")
            foods = [{
                "name": f["name"], "grams": f["grams"], "calories": f["calories"]
            } for f in recognized if isinstance(f, dict) and f.get("meal") == meal_name]
            meals.append({
                "meal_type": meal_name,
                "time": meal_time,
                "total_calories": int(b.get("calories", bd_map.get(meal_name, {}).get("calories", 0))),
                "foods": foods,
            })
        _mark(sources, "meals.*.meal_type", "db")
        _mark(sources, "meals.*.time", "db")
        _mark(sources, "meals.*.foods", "db")
    elif has_nut and breakdown:
        # 有 breakdown 但无 recognized_foods：仅给出餐次汇总
        meals = [{
            "meal_type": b["meal"] if isinstance(b, dict) else "未知",
            "time": b.get("time", "12:00") if isinstance(b, dict) else "12:00",
            "total_calories": int(b.get("calories", 0)) if isinstance(b, dict) else 0,
            "foods": [],
        } for b in breakdown if isinstance(b, dict)]
        _mark(sources, "meals.*.meal_type", "db")
        _mark(sources, "meals.*.time", "db")
        _mark(sources, "meals.*.foods", "mock")
    else:
        # mock 兜底（无数据日）
        _MEALS_MOCK = [
            {"meal_type": "早餐", "time": "08:30", "total_calories": 271,
             "foods": [{"name": "鸡蛋", "grams": 100, "calories": 155},
                       {"name": "牛奶", "grams": 200, "calories": 108}]},
            {"meal_type": "午餐", "time": "12:30", "total_calories": 523,
             "foods": [{"name": "鸡胸肉", "grams": 150, "calories": 248},
                       {"name": "西兰花", "grams": 100, "calories": 34}]},
            {"meal_type": "晚餐", "time": "18:30", "total_calories": 486,
             "foods": [{"name": "鸡胸肉", "grams": 120, "calories": 198},
                       {"name": "牛奶", "grams": 150, "calories": 81}]},
        ]
        meals = list(_MEALS_MOCK)
        _mark(sources, "meals", "mock")
        _mark(sources, "meals.*.foods", "mock")

    # --- exercise_advice: user_plans.training_plan → 规则兜底 ---
    plan = _query_one(
        "SELECT training_plan FROM user_plans "
        "WHERE user_id = %s ORDER BY plan_date DESC LIMIT 1",
        (user_id,),
    )
    if plan:
        tp = plan.get("training_plan") or {}
        exercises = tp.get("exercises") or _MOCK_NUTRITION_EXERCISE_ADVICE["exercises"]
        # 保持 exercises 输出格式一致：name+(sets/reps 或 duration)
        ex_list = []
        for ex in exercises:
            if isinstance(ex, dict):
                item = {"name": ex.get("name", "训练")}
                if ex.get("sets") and ex.get("reps"):
                    item["sets"] = ex["sets"]
                    item["reps"] = ex["reps"]
                elif ex.get("duration"):
                    item["duration"] = ex["duration"]
                ex_list.append(item)
        exercise_advice = {
            "training_type": tp.get("training_type", "有氧训练"),
            "duration": f"{tp.get('target_duration_min', 40)}-{tp.get('target_duration_min', 40) + 20}分钟"
                        if tp.get("target_duration_min") else "40-60分钟",
            "calorie_target": tp.get("target_total_kcal", 400),
            "exercises": ex_list,
        }
        _mark(sources, "exercise_advice", "db")
    else:
        exercise_advice = dict(_MOCK_NUTRITION_EXERCISE_ADVICE)
        _mark(sources, "exercise_advice", "mock")

    return {
        "user_id": user_id,
        "date": on_date,
        "nutrition": {
            "kpi": {
                "goal_calories": goal_cal,
                "intake_calories": intake_calories or 0,
                "remaining_calories": remaining_calories,
                "achievement_rate": achievement_rate,
            },
            "energy": {
                "total_calories": intake_calories or 0,
                "macros": macros,
                "recommended_calories": recommended_calories,
                "bmr": bmr_val,
                "exercise_burn": exercise_burn,
                "energy_gap": energy_gap,
            },
            "meals": meals,
            "exercise_advice": exercise_advice,
        },
        "sources": sources,
    }


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
    g = _get_goals(profile)  # 统一缺省常量 10000/60/2000/500
    goals = profile.get("goals") or {}
    steps_goal = g["steps_goal"]
    ex_goal = g["exercise_minutes_goal"]

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
