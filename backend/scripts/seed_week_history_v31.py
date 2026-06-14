#!/usr/bin/env python3
"""
v3.1 历史数据构造器 —— A/B 两用户最近 14 天，写齐「新表结构 + 旧 JSONB 镜像（双写）」。

对齐：
- 数据协议 v3.1 / tables_v3.1_full.sql（结构化列 + user_plans/user_executions/sleep_log）
- 三个前端页面（运动/睡眠/饮食）与其接口模型（health_data 取数：结构化列优先、镜像回退）
- 业务剧情：user=1 向好周(improving)、user=2 恶化周(degrading)

写入：
- watch_data       结构化睡眠/身体/心血管列 + sleep_data/hrv_data JSONB 镜像
- exercise_records 结构化执行列 + start_time/end_time/distance_km + analysis_result 镜像
                   （今日写 3 条：户外跑步/力量训练/瑜伽，匹配运动页"今日运动记录"）
- nutrition_logs   结构化宏量列 + recognized_foods(结构化单品) + meal_breakdown + nutrition_result 镜像
                   （食材对齐前端图标集：牛奶/鸡蛋/包子/鸡胸肉/西兰花）
- user_plans       training_plan(动作=深蹲/俯卧撑/硬拉/拉伸放松) / sleep_plan / diet_plan（建议与方案源）
- user_executions  v3.1 执行包（body_state/cardiovascular/sleep/exercise/diet_execution）
- sleep_log        手动录入睡眠真值源
- users            体测 + body_age + goals(10000/60/2000/500 …)

幂等：插入前删除窗口内旧行；自带 ADD COLUMN/CREATE TABLE IF NOT EXISTS，可在现有库直接跑。
运行：python backend/scripts/seed_week_history_v31.py   （HPU-3.12 环境）
"""

from __future__ import annotations

import os
import sys
import random
from datetime import date, datetime, time, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import Json

from store.db import get_connection_params

DAYS = 14
random.seed(42)
CA = 30  # chronological age（两个演示用户都 30 岁）

# ---------------- 剧情端点（DAYS 天前 -> 今天）----------------
ARCS = {
    "improving": {
        "sleep_score": (70, 86), "hrv": (38, 48), "rhr": (64, 56),
        "steps": (6000, 9200), "ex_min": (35, 60), "burn": (320, 520),
        "intake": (2100, 1850), "protein": (95, 132), "balance": (68, 88),
        "weight": (73.5, 72.0), "body_fat": (20.5, 18.7), "muscle": (54.2, 55.5),
        "rpe": (5, 6), "completion": (0.85, 1.0), "adherence": (0.7, 0.95),
        "choice": "comply",
    },
    "degrading": {
        "sleep_score": (78, 56), "hrv": (46, 30), "rhr": (60, 70),
        "steps": (8500, 5200), "ex_min": (70, 25), "burn": (560, 240),
        "intake": (1900, 2350), "protein": (120, 78), "balance": (82, 52),
        "weight": (79.0, 80.5), "body_fat": (22.0, 24.5), "muscle": (56.0, 54.8),
        "rpe": (6, 9), "completion": (0.9, 0.4), "adherence": (0.8, 0.4),
        "choice": "reject",
    },
}

GOALS = {
    "steps_goal": 10000,
    "exercise_minutes_goal": 60,
    "exercise_days_goal": 7,
    "calorie_burn_target": 500,
    "calorie_intake_target": 2000,
    "exercise_duration_target": "40-60",
    "calorie_burn_session_target": "320-450",
    "sleep_recommend_min": 7,
    "sleep_recommend_max": 9,
    "nap_recommend_min": 20,
    "nap_recommend_max": 30,
}

# ---------------- 食材目录（对齐前端 page-nutrition 图标集；每 100g）----------------
FOODS = {
    "牛奶":   {"kcal": 54,  "protein": 3.4,  "fdc": 746782},
    "鸡蛋":   {"kcal": 155, "protein": 13.0, "fdc": 171287},
    "包子":   {"kcal": 227, "protein": 7.0,  "fdc": None},
    "鸡胸肉": {"kcal": 165, "protein": 31.0, "fdc": 171477},
    "西兰花": {"kcal": 34,  "protein": 2.8,  "fdc": 170379},
}
# 每餐模板：(餐别, 时间, [(食材, 克数), ...])
MEAL_TEMPLATE = [
    ("早餐", "08:30", [("牛奶", 200), ("鸡蛋", 100), ("包子", 80)]),
    ("午餐", "12:30", [("鸡胸肉", 150), ("西兰花", 150), ("鸡蛋", 50)]),
    ("晚餐", "18:30", [("鸡胸肉", 120), ("西兰花", 100), ("牛奶", 150)]),
    ("加餐", "15:30", [("牛奶", 150)]),
]
# 训练方案动作（对齐 page-nutrition 图标集）+ wger external_id 占位
PLAN_EXERCISES = [
    {"name": "深蹲", "external_id": 1748, "external_source": "wger", "sets": 4, "reps": 12, "rest_seconds": 60, "intensity": "medium"},
    {"name": "俯卧撑", "external_id": 195, "external_source": "wger", "sets": 4, "reps": 12, "rest_seconds": 60, "intensity": "medium"},
    {"name": "硬拉", "external_id": 105, "external_source": "wger", "sets": 4, "reps": 12, "rest_seconds": 90, "intensity": "high"},
    {"name": "拉伸放松", "external_id": 789, "external_source": "wger", "sets": 1, "reps": 1, "rest_seconds": 0, "intensity": "low", "duration": "10分钟"},
]


def _lerp(a, b, t):
    return a + (b - a) * t


def _jit(amp):
    return (random.random() - 0.5) * 2 * amp


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _sleep_stages_timeline(total_hours, deep_pct):
    hours = max(5, round(total_hours))
    tl = []
    for h in range(hours):
        deep = max(0, round(60 * (deep_pct / 100) * (1.4 if h < hours / 2 else 0.5)))
        rem = max(0, round(60 * 0.22 * (0.5 if h < hours / 2 else 1.4)))
        awake = 5 if h in (0, hours - 1) else 0
        light = max(0, 60 - deep - rem - awake)
        tl.append({"hour": h, "deep": deep, "light": light, "rem": rem, "awake": awake})
    return tl


def _hhmm_minus(wake_hhmm: str, total_hours: float) -> str:
    """由起床时间与总时长反推入睡时间(HH:MM)。"""
    wh, wm = map(int, wake_hhmm.split(":"))
    wake_min = wh * 60 + wm
    bed_min = (wake_min - int(round(total_hours * 60))) % (24 * 60)
    return f"{bed_min // 60:02d}:{bed_min % 60:02d}"


def _rr_series(rhr: int) -> list:
    """深睡期 10 段 RR 间期(ms)，约 60000/HR。"""
    base = 60000.0 / max(40, rhr - 6)  # 睡眠心率略低于静息
    return [int(round(base + _jit(18))) for _ in range(10)]


def _build_meals(intake_target: int, weight_kg: float):
    """按模板生成 recognized_foods + meal_breakdown，并缩放到接近目标摄入。"""
    # 先按模板原始克数算基准热量
    base_total = 0.0
    for _, _, items in MEAL_TEMPLATE:
        for name, g in items:
            base_total += FOODS[name]["kcal"] * g / 100.0
    scale = intake_target / base_total if base_total else 1.0

    recognized, breakdown = [], []
    total_cal = total_pro = 0.0
    for meal, mtime, items in MEAL_TEMPLATE:
        m_cal = m_pro = 0.0
        for name, g in items:
            gg = int(round(g * scale))
            cal = int(round(FOODS[name]["kcal"] * gg / 100.0))
            pro = round(FOODS[name]["protein"] * gg / 100.0, 1)
            recognized.append({
                "meal": meal, "time": mtime, "name": name, "grams": gg,
                "calories": cal, "protein_g": pro,
                "external_id": FOODS[name]["fdc"], "external_source": "usda",
            })
            m_cal += cal
            m_pro += pro
        breakdown.append({"meal": meal, "time": mtime, "calories": int(m_cal), "protein_g": int(round(m_pro))})
        total_cal += m_cal
        total_pro += m_pro
    return recognized, breakdown, int(total_cal), int(round(total_pro))


# =============================================================================
# 预计算每日指标（便于算 hrv_trend_7d 等跨日衍生）
# =============================================================================
def precompute(arc_name: str):
    arc = ARCS[arc_name]
    days = []
    for i in range(DAYS):
        t = i / (DAYS - 1)
        sleep_score = int(round(_clamp(_lerp(*arc["sleep_score"], t) + _jit(2), 40, 95)))
        hrv = round(_clamp(_lerp(*arc["hrv"], t) + _jit(1.5), 20, 80), 1)
        rhr = int(round(_clamp(_lerp(*arc["rhr"], t) + _jit(1), 50, 90)))
        steps = max(0, int(round(_lerp(*arc["steps"], t) + _jit(600))))
        ex_min = max(0, int(round(_lerp(*arc["ex_min"], t) + _jit(8))))
        intake = int(round(_lerp(*arc["intake"], t) + _jit(80)))
        protein = int(round(_lerp(*arc["protein"], t) + _jit(6)))
        balance = round(_clamp(_lerp(*arc["balance"], t) + _jit(4), 0, 100), 1)
        weight = round(_lerp(*arc["weight"], t), 1)
        body_fat = round(_lerp(*arc["body_fat"], t), 1)
        muscle = round(_lerp(*arc["muscle"], t), 1)
        rpe = int(round(_clamp(_lerp(*arc["rpe"], t), 1, 10)))
        completion = round(_clamp(_lerp(*arc["completion"], t), 0.0, 1.0), 2)
        adherence = round(_clamp(_lerp(*arc["adherence"], t), 0.0, 1.0), 2)
        total_hours = round(_clamp(sleep_score / 12.0 + 1.0, 5.0, 9.5), 1)
        deep_pct = int(round(_clamp(sleep_score / 4, 8, 28)))
        days.append(dict(
            sleep_score=sleep_score, hrv=hrv, rhr=rhr, steps=steps, ex_min=ex_min,
            intake=intake, protein=protein, balance=balance, weight=weight,
            body_fat=body_fat, muscle=muscle, rpe=rpe, completion=completion,
            adherence=adherence, total_hours=total_hours, deep_pct=deep_pct,
        ))
    # hrv_trend_7d：与 7 天前比
    for i, d in enumerate(days):
        if i >= 7 and days[i - 7]["hrv"]:
            d["hrv_trend_7d"] = round((d["hrv"] - days[i - 7]["hrv"]) / days[i - 7]["hrv"] * 100, 1)
        else:
            d["hrv_trend_7d"] = None
    return days


# =============================================================================
# 写入
# =============================================================================
def seed_week(conn, uid: int, arc_name: str):
    arc = ARCS[arc_name]
    today = date.today()
    start = today - timedelta(days=DAYS - 1)
    metrics = precompute(arc_name)

    with conn.cursor() as cur:
        # 幂等清理窗口内旧数据
        cur.execute("DELETE FROM watch_data       WHERE user_id=%s AND date >= %s", (uid, start))
        cur.execute("DELETE FROM exercise_records WHERE user_id=%s AND date >= %s", (uid, start))
        cur.execute("DELETE FROM nutrition_logs   WHERE user_id=%s AND date >= %s", (uid, start))
        cur.execute("DELETE FROM user_plans       WHERE user_id=%s AND plan_date >= %s", (uid, start))
        cur.execute("DELETE FROM user_executions  WHERE user_id=%s AND exec_date >= %s", (uid, start))
        cur.execute("DELETE FROM sleep_log        WHERE user_id=%s AND sleep_date >= %s", (uid, start))

        last = {}
        for i in range(DAYS):
            d = start + timedelta(days=i)
            is_today = (i == DAYS - 1)
            m = metrics[i]

            # 休息日：周三/周日，但今日强制训练日（保证页面非零）
            rest_day = (d.weekday() in (2, 6)) and not is_today
            ex_min = 0 if rest_day else m["ex_min"]
            burn = int(round(_lerp(*arc["burn"], i / (DAYS - 1)) + _jit(40))) if ex_min else 0

            # ---- 睡眠衍生 ----
            total_hours = m["total_hours"]
            total_min = int(round(total_hours * 60))
            deep_min = int(round(total_min * m["deep_pct"] / 100))
            rem_min = int(round(total_min * 0.22))
            awake_min = max(5, round((100 - m["sleep_score"]) / 3))
            light_min = max(0, total_min - deep_min - rem_min - awake_min)
            deep_pct_f = round(deep_min / total_min, 2) if total_min else None
            sleep_eff = round(total_min / (total_min + awake_min), 2) if total_min else None
            wake_hhmm = "06:40" if arc_name == "improving" else ("07:20" if m["sleep_score"] >= 60 else "06:10")
            bed_hhmm = _hhmm_minus(wake_hhmm, total_hours)
            nap_min = 20 if (rest_day and arc_name == "improving") else 0
            nap_score = 80 if nap_min else 0

            # ---- 身体/心血管 ----
            weight, body_fat, muscle = m["weight"], m["body_fat"], m["muscle"]
            lean = round(weight * (1 - body_fat / 100), 2)
            body_age = round(_clamp(CA + 0.4 * (m["rhr"] - 60) + 1.2 * (7.5 - total_hours), CA - 5, CA + 12), 1)
            rmssd, rhr = m["hrv"], m["rhr"]
            hrv_data = {"rmssd": rmssd, "sdnn": round(rmssd * 1.2, 1), "pnn50": round(_clamp(rmssd / 2, 1, 40), 1),
                        "lf_hf_ratio": round(1.0 + (70 - rhr) / 50, 2)}

            # ---- 运动执行（聚合 HRR）----
            peak = rhr + (95 if arc_name == "degrading" else 80) if ex_min else None
            hr60 = (peak - (12 if arc_name == "degrading" else 22)) if ex_min else None
            hrr = (peak - hr60) if (peak and hr60) else None
            avg_hr = (rhr + 50) if ex_min else None

            sleep_data = {
                "sleep_score": m["sleep_score"], "total_hours": total_hours,
                "deep_sleep_percent": m["deep_pct"], "rem_sleep_percent": 22,
                "bedtime": bed_hhmm, "wake_time": wake_hhmm, "nap_minutes": nap_min,
                "stages_timeline": _sleep_stages_timeline(total_hours, m["deep_pct"]),
            }

            # ---------- watch_data（结构化列 + JSONB 镜像）----------
            cur.execute(
                """
                INSERT INTO watch_data
                  (user_id, date, steps, exercise_minutes, calories_burned,
                   heart_rate_avg, heart_rate_rest, heart_rate_max, stress_level, blood_oxygen,
                   weight_kg, body_fat_pct, body_age, lean_mass_kg,
                   hrv_data, hrv_trend_7d, hrr,
                   actual_bedtime, actual_wake_time, total_sleep_min, deep_sleep_min,
                   light_sleep_min, rem_sleep_min, awake_min, deep_sleep_pct, sleep_efficiency,
                   rr_intervals, rr_extraction_window, nap_min, nap_score, sleep_data)
                VALUES (%s,%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,
                        %s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s, %s)
                """,
                (uid, d, m["steps"], ex_min, burn,
                 rhr + 14, rhr, (peak or rhr + 40), int(_clamp(100 - m["sleep_score"] + m["rpe"] * 4, 10, 90)),
                 97 if arc_name == "improving" else 95,
                 weight, body_fat, body_age, lean,
                 Json(hrv_data), m["hrv_trend_7d"], hrr,
                 bed_hhmm, wake_hhmm, total_min, deep_min,
                 light_min, rem_min, awake_min, deep_pct_f, sleep_eff,
                 Json(_rr_series(rhr)), f"{bed_hhmm}-04:00", nap_min, nap_score, Json(sleep_data)),
            )

            # ---------- exercise_records（训练日；今日写 3 条）----------
            if ex_min:
                if is_today:
                    sessions = [
                        ("户外跑步", round(ex_min * 0.5), 6.0, "16:40", "17:20"),
                        ("力量训练", round(ex_min * 0.3), None, "17:30", "18:00"),
                        ("瑜伽",    round(ex_min * 0.2), None, "20:00", "20:30"),
                    ]
                else:
                    typ = "户外跑步" if i % 3 == 0 else ("力量训练" if i % 3 == 1 else "瑜伽")
                    dist = round(2.0 + _jit(1.5) + (i % 4), 1) if typ == "户外跑步" else None
                    sessions = [(typ, ex_min, dist, "18:00", f"18:{min(59, ex_min):02d}")]
                n = len(sessions)
                for si, (typ, dur, dist, st, et) in enumerate(sessions):
                    cal_i = int(round(burn / n))
                    rpe_i = m["rpe"]
                    cur.execute(
                        """
                        INSERT INTO exercise_records
                          (user_id, date, exercise_type, form_quality,
                           user_choice, actual_duration_min, actual_rpe, avg_hr, peak_hr, hr_60s_after,
                           calories_burned, completion_rate, completion_rate_display,
                           start_time, end_time, distance_km, analysis_result)
                        VALUES (%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s, %s)
                        """,
                        (uid, d, typ, "good" if arc_name == "improving" else "fair",
                         arc["choice"], dur, rpe_i, avg_hr, peak, hr60,
                         cal_i, m["completion"], int(round(m["completion"] * 100)),
                         st, et, dist,
                         Json({"duration_minutes": dur, "peak_hr": peak, "hr_60s": hr60,
                               "rpe": rpe_i, "calories": cal_i, "time_range": f"{st}-{et}",
                               "distance_km": dist})),
                    )

            # ---------- nutrition_logs（结构化 + 单品 + 镜像）----------
            # 结构化宏量列用剧情值（真实趋势）；recognized_foods/meal_breakdown 为图标对齐的展示明细
            recognized, breakdown, _meal_cal, _meal_pro = _build_meals(m["intake"], weight)
            intake = m["intake"]
            protein = m["protein"]
            carbs = int(round(intake * 0.45 / 4))
            fat = int(round(intake * 0.27 / 9))
            remaining = GOALS["calorie_intake_target"] - intake
            ppk = round(protein / weight, 2) if weight else None
            narrative = "；".join(
                f"{b['meal']}：" + "、".join(f"{x['name']}{x['grams']}g" for x in recognized if x["meal"] == b["meal"])
                for b in breakdown
            )
            cur.execute(
                """
                INSERT INTO nutrition_logs
                  (user_id, date, meal_type, balance_score,
                   total_calories_actual, calories_remaining, protein_g, carbs_g, fat_g,
                   protein_per_kg, adherence_rate, narrative,
                   recognized_foods, meal_breakdown, nutrition_result)
                VALUES (%s,%s,%s,%s, %s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s)
                """,
                (uid, d, "daily", m["balance"],
                 intake, remaining, protein, carbs, fat,
                 ppk, m["adherence"], narrative,
                 Json(recognized), Json(breakdown),
                 Json({"total_calories": intake, "protein_g": protein, "carbs_g": carbs,
                       "fat_g": fat, "diet_narrative": narrative})),
            )

            # ---------- user_plans（计划：建议 + 训练方案源）----------
            training_type = "recovery" if (arc_name == "improving" and rest_day) else (
                "strength" if arc_name == "improving" else "recovery")
            training_plan = {
                "date": d.isoformat(), "training_type": training_type,
                "reason": ("昨日 HRV 回升、RPE 适中，安排力量/恢复训练巩固适应。" if arc_name == "improving"
                           else "连日高强度导致 HRV 下滑，建议降载恢复（用户当日选择硬练）。"),
                "target_total_kcal": GOALS["calorie_burn_target"], "target_duration_min": GOALS["exercise_minutes_goal"],
                "target_avg_hr": 120, "target_peak_hr": 150, "target_rpe": m["rpe"],
                "exercises": PLAN_EXERCISES, "safety_flags": [],
            }
            sleep_plan = {
                "date": d.isoformat(), "target_bedtime": "23:00", "target_wake_time": "06:30",
                "target_duration_h": 7.5, "target_sleep_score": 85,
                "suggestions": [
                    {"title": "睡前 1 小时关闭电子屏幕", "category": "screen", "action": "手机调灰度并移出卧室，减少蓝光抑制褪黑素。"},
                    {"title": "卧室温度保持 18-20℃", "category": "temperature", "action": "睡前 30 分钟开空调，核心体温下降助快速入睡。"},
                ],
            }
            diet_plan = {
                "date": d.isoformat(), "total_calories_target": GOALS["calorie_intake_target"],
                "macros": {"protein_g": 140, "carbs_g": 200, "fat_g": 60},
                "meals": [{"meal": b["meal"],
                           "foods": [{"name": x["name"], "external_id": x["external_id"], "external_source": "usda",
                                      "amount_g": x["grams"], "calories": x["calories"], "protein_g": x["protein_g"]}
                                     for x in recognized if x["meal"] == b["meal"]]}
                          for b in breakdown],
                "sauce_compensation_applied": True, "sauce_factor": 1.30,
                "notes": "沙拉酱按 1.30 系数代偿扣除。",
            }
            cur.execute(
                """
                INSERT INTO user_plans (user_id, plan_date, training_plan, sleep_plan, diet_plan, source)
                VALUES (%s,%s,%s,%s,%s,'agent')
                ON CONFLICT (user_id, plan_date) DO UPDATE SET
                    training_plan=EXCLUDED.training_plan, sleep_plan=EXCLUDED.sleep_plan,
                    diet_plan=EXCLUDED.diet_plan, updated_at=CURRENT_TIMESTAMP
                """,
                (uid, d, Json(training_plan), Json(sleep_plan), Json(diet_plan)),
            )

            # ---------- user_executions（v3.1 执行包）----------
            execution = {
                "body_state": {"date": d.isoformat(), "weight_kg": weight, "body_fat_pct": body_fat,
                               "body_age": body_age, "lean_mass_kg": lean},
                "cardiovascular": {"date": d.isoformat(), "resting_hr": rhr, "hrv_rmssd": rmssd,
                                   "hrr": hrr, "hrv_trend_7d": m["hrv_trend_7d"]},
                "sleep_execution": {"date": d.isoformat(), "actual_bedtime": bed_hhmm, "actual_wake_time": wake_hhmm,
                                    "total_sleep_min": total_min, "sleep_score": m["sleep_score"],
                                    "deep_sleep_min": deep_min, "deep_sleep_pct": deep_pct_f,
                                    "light_sleep_min": light_min, "rem_sleep_min": rem_min,
                                    "awake_min": awake_min, "sleep_efficiency": sleep_eff},
                "exercise_execution": {"date": d.isoformat(), "user_choice": arc["choice"],
                                       "actual_duration_min": ex_min, "actual_rpe": m["rpe"],
                                       "avg_hr": avg_hr, "peak_hr": peak, "hr_60s_after": hr60,
                                       "calories_burned": burn, "completion_rate": m["completion"],
                                       "completion_rate_display": int(round(m["completion"] * 100))},
                "diet_execution": {"date": d.isoformat(), "total_calories_actual": intake,
                                   "calories_remaining": remaining,
                                   "macros_actual": {"protein_g": protein, "carbs_g": carbs, "fat_g": fat,
                                                     "protein_per_kg": ppk},
                                   "adherence_rate": m["adherence"], "narrative": narrative,
                                   "meal_breakdown": breakdown},
            }
            cur.execute(
                """
                INSERT INTO user_executions
                  (user_id, exec_date, user_choice, body_state, cardiovascular,
                   sleep_execution, exercise_execution, diet_execution, source)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'simulator')
                ON CONFLICT (user_id, exec_date) DO UPDATE SET
                    user_choice=EXCLUDED.user_choice, body_state=EXCLUDED.body_state,
                    cardiovascular=EXCLUDED.cardiovascular, sleep_execution=EXCLUDED.sleep_execution,
                    exercise_execution=EXCLUDED.exercise_execution, diet_execution=EXCLUDED.diet_execution
                """,
                (uid, d, arc["choice"], Json(execution["body_state"]), Json(execution["cardiovascular"]),
                 Json(execution["sleep_execution"]), Json(execution["exercise_execution"]),
                 Json(execution["diet_execution"])),
            )

            # ---------- sleep_log（录入真值源）----------
            bed_dt = datetime.combine(d - timedelta(days=1) if bed_hhmm >= "12:00" else d,
                                      time(*map(int, bed_hhmm.split(":"))))
            wake_dt = datetime.combine(d, time(*map(int, wake_hhmm.split(":"))))
            if wake_dt <= bed_dt:
                wake_dt += timedelta(days=1)
            cur.execute(
                """
                INSERT INTO sleep_log (user_id, sleep_date, bedtime_at, wake_time_at, source, note)
                VALUES (%s,%s,%s,%s,'user_input',%s)
                ON CONFLICT (user_id, sleep_date) DO UPDATE SET
                    bedtime_at=EXCLUDED.bedtime_at, wake_time_at=EXCLUDED.wake_time_at,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (uid, d, bed_dt, wake_dt, "种子录入"),
            )

            last = {"weight": weight, "body_fat": body_fat, "muscle": muscle, "body_age": body_age}

        # users：当前体测 + body_age + goals
        cur.execute(
            """
            UPDATE users SET weight_kg=%s, body_fat_pct=%s, muscle_mass_kg=%s, body_age=%s,
                             goals=%s, chronological_age=%s, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            (last["weight"], last["body_fat"], last["muscle"], last["body_age"], Json(GOALS), CA, uid),
        )
    print(f"  user={uid} arc={arc_name}: 写入 {DAYS} 天 watch/exercise/nutrition/plans/executions/sleep_log + users")


# =============================================================================
# 幂等 DDL（自含：可在现有库直接跑；与 tables_v3.1_full.sql / migrate_v3_1_aligned.sql 一致）
# =============================================================================
def ensure_ddl(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS TRIGGER AS $$ "
                    "BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END $$ LANGUAGE plpgsql;")
        # users
        for col, typ in [("body_fat_pct", "FLOAT"), ("muscle_mass_kg", "FLOAT"), ("body_age", "FLOAT"),
                         ("goals", "JSONB"), ("chronological_age", "INT"), ("schema_version", "VARCHAR(20)"),
                         ("tz_offset", "VARCHAR(10)")]:
            cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typ}")
        # ai_conversations 兼容补丁
        for col, typ in [("messages", "JSONB"), ("speech_report", "TEXT"), ("recommendations", "JSONB")]:
            cur.execute(f"ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS {col} {typ}")
        # watch_data 结构化列
        for col, typ in [("weight_kg", "FLOAT"), ("body_fat_pct", "FLOAT"), ("body_age", "FLOAT"),
                         ("lean_mass_kg", "FLOAT"), ("hrv_trend_7d", "FLOAT"), ("hrr", "INT"),
                         ("actual_bedtime", "VARCHAR(5)"), ("actual_wake_time", "VARCHAR(5)"),
                         ("total_sleep_min", "INT"), ("deep_sleep_min", "INT"), ("light_sleep_min", "INT"),
                         ("rem_sleep_min", "INT"), ("awake_min", "INT"), ("deep_sleep_pct", "FLOAT"),
                         ("sleep_efficiency", "FLOAT"), ("rr_intervals", "JSONB"),
                         ("rr_extraction_window", "VARCHAR(20)"), ("nap_min", "INT"), ("nap_score", "INT")]:
            cur.execute(f"ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS {col} {typ}")
        # exercise_records 结构化列 + 缺口列
        for col, typ in [("user_choice", "VARCHAR(20)"), ("actual_duration_min", "INT"), ("actual_rpe", "INT"),
                         ("avg_hr", "INT"), ("peak_hr", "INT"), ("hr_60s_after", "INT"),
                         ("calories_burned", "INT"), ("completion_rate", "FLOAT"),
                         ("completion_rate_display", "INT"), ("start_time", "TIME"),
                         ("end_time", "TIME"), ("distance_km", "FLOAT")]:
            cur.execute(f"ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS {col} {typ}")
        # nutrition_logs 结构化列
        for col, typ in [("total_calories_actual", "INT"), ("calories_remaining", "INT"), ("protein_g", "INT"),
                         ("carbs_g", "INT"), ("fat_g", "INT"), ("protein_per_kg", "FLOAT"),
                         ("adherence_rate", "FLOAT"), ("narrative", "TEXT"), ("meal_breakdown", "JSONB")]:
            cur.execute(f"ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS {col} {typ}")
        # 新表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_plans (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                plan_date DATE NOT NULL,
                training_plan JSONB, sleep_plan JSONB, diet_plan JSONB,
                source VARCHAR(50) DEFAULT 'agent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_user_plans_user_date UNIQUE (user_id, plan_date))""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_executions (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                exec_date DATE NOT NULL,
                user_choice VARCHAR(20),
                body_state JSONB, cardiovascular JSONB, sleep_execution JSONB,
                exercise_execution JSONB, diet_execution JSONB,
                source VARCHAR(50) DEFAULT 'simulator',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_user_executions_user_date UNIQUE (user_id, exec_date))""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sleep_log (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                sleep_date DATE NOT NULL,
                bedtime_at TIMESTAMP NOT NULL, wake_time_at TIMESTAMP NOT NULL,
                source VARCHAR(20) DEFAULT 'user_input', note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_sleep_log_user_date UNIQUE (user_id, sleep_date),
                CONSTRAINT ck_sleep_log_wake_after_bed CHECK (wake_time_at > bedtime_at))""")


def ensure_user(conn, uid, name, age, gender, height, weight):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (id, name, age, gender, height_cm, weight_kg,
                               fitness_level, goal, activity_level, chronological_age)
            VALUES (%s,%s,%s,%s,%s,%s,'intermediate','lose_weight','moderate',%s)
            ON CONFLICT (id) DO UPDATE SET age=EXCLUDED.age, height_cm=EXCLUDED.height_cm
            """,
            (uid, name, age, gender, height, weight, age),
        )


def main():
    conn = psycopg2.connect(**get_connection_params())
    try:
        ensure_ddl(conn)
        ensure_user(conn, 1, "小明", CA, "male", 175, 72)
        ensure_user(conn, 2, "小强(恶化对照)", CA, "male", 178, 80)
        print("开始造 v3.1 数据（最近 %d 天）..." % DAYS)
        seed_week(conn, 1, "improving")
        seed_week(conn, 2, "degrading")
        conn.commit()
        print("✅ 完成。user=1 向好周；user=2 恶化周（含 plans/executions/sleep_log + 结构化列 + JSONB 镜像）。")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
