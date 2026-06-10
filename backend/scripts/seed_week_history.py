#!/usr/bin/env python3
"""
造一周（实为最近 14 天：本周 + 上周，便于算"较上周↑"）健康历史数据。

- user=1：向好周（指标小幅改善，适配仪表盘"89分/低风险/较上周↑"）
- user=2：恶化周（过训→指标走低，演示对照）

写入 watch_data / exercise_records / nutrition_logs，并设置 users 的
weight_kg / body_fat_pct / muscle_mass_kg / goals。

幂等：插入前先删除该用户在窗口内的旧行，可反复重跑。
运行：python backend/scripts/seed_week_history.py   （HPU-3.12 环境）
"""

from __future__ import annotations

import os
import sys
import random
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import Json

from store.db import get_connection_params

DAYS = 14          # 最近 14 天（本周 + 上周）
random.seed(42)    # 可复现

# 各"剧情"的指标端点：从 DAYS 天前 -> 今天 的走向
ARCS = {
    "improving": {
        "sleep_score": (70, 86), "hrv": (38, 48), "rhr": (64, 56),
        "steps": (6000, 9200), "ex_min": (35, 65), "burn": (320, 560),
        "intake": (2100, 1850), "protein": (95, 132), "balance": (68, 88),
        "weight": (73.5, 72.0), "body_fat": (20.5, 18.7), "muscle": (54.2, 55.5),
        "rpe": (5, 6),
    },
    "degrading": {
        "sleep_score": (78, 56), "hrv": (46, 30), "rhr": (60, 70),
        "steps": (8500, 5200), "ex_min": (70, 25), "burn": (560, 240),
        "intake": (1900, 2350), "protein": (120, 78), "balance": (82, 52),
        "weight": (79.0, 80.5), "body_fat": (22.0, 24.5), "muscle": (56.0, 54.8),
        "rpe": (6, 9),
    },
}

GOALS = {
    "steps_goal": 8000,
    "exercise_minutes_goal": 30,       # 单日"运动达标"阈值
    "exercise_days_goal": 7,
    "calorie_burn_target": 500,
    "calorie_intake_target": 1800,
    "exercise_duration_target": "40-60",      # 推荐运动时长(分钟)
    "calorie_burn_session_target": "320-450",  # 单次消耗目标(千卡)
}

DIET_NARRATIVES = [
    "早餐：燕麦牛奶+鸡蛋；午餐：鸡胸肉糙米饭西兰花；晚餐：三文鱼藜麦沙拉。",
    "早餐：希腊酸奶坚果蓝莓；午餐：牛肉糙米饭；晚餐：鸡胸肉蔬菜。",
    "早餐：全麦面包煎蛋；午餐：三文鱼糙米饭；晚餐：豆腐青菜。",
]
DIET_NARRATIVES_BAD = [
    "早餐：油条甜豆浆；午餐：凯撒沙拉多加酱红烧肉盖饭；晚餐：炸鸡啤酒，宵夜方便面。",
    "早餐：包子+含糖奶茶；午餐：黄焖鸡米饭；晚餐：火锅+可乐。",
]


def _lerp(a, b, t):
    return a + (b - a) * t


def _jit(idx, amp):
    """按天序做小幅确定性扰动，让曲线自然。"""
    return (random.random() - 0.5) * 2 * amp


def _sleep_stages_timeline(total_hours, deep_pct):
    """生成逐小时浅睡/深睡/REM/清醒分钟序列（柱状图用）。"""
    hours = max(5, round(total_hours))
    timeline = []
    for h in range(hours):
        # 前半夜深睡多，后半夜 REM/浅睡多
        deep = max(0, round(60 * (deep_pct / 100) * (1.4 if h < hours / 2 else 0.5)))
        rem = max(0, round(60 * 0.22 * (0.5 if h < hours / 2 else 1.4)))
        awake = 5 if h in (0, hours - 1) else 0
        light = max(0, 60 - deep - rem - awake)
        timeline.append({"hour": h, "deep": deep, "light": light, "rem": rem, "awake": awake})
    return timeline


def seed_week(conn, uid: int, arc_name: str):
    arc = ARCS[arc_name]
    today = date.today()
    start = today - timedelta(days=DAYS - 1)

    with conn.cursor() as cur:
        # 幂等清理窗口内旧数据
        for tbl in ("watch_data", "exercise_records", "nutrition_logs"):
            cur.execute(f"DELETE FROM {tbl} WHERE user_id = %s AND date >= %s", (uid, start))

        diet_pool = DIET_NARRATIVES if arc_name == "improving" else DIET_NARRATIVES_BAD
        last = {}
        for i in range(DAYS):
            d = start + timedelta(days=i)
            t = i / (DAYS - 1)

            sleep_score = int(round(_lerp(arc["sleep_score"][0], arc["sleep_score"][1], t) + _jit(i, 2)))
            hrv = round(_lerp(arc["hrv"][0], arc["hrv"][1], t) + _jit(i, 1.5), 1)
            rhr = int(round(_lerp(arc["rhr"][0], arc["rhr"][1], t) + _jit(i, 1)))
            steps = int(round(_lerp(arc["steps"][0], arc["steps"][1], t) + _jit(i, 600)))
            ex_min = max(0, int(round(_lerp(arc["ex_min"][0], arc["ex_min"][1], t) + _jit(i, 8))))
            # 每周两个休息日；但保证最后一天(今日)为训练日，让仪表盘"今日运动"非零
            if d.weekday() in (2, 6) and i != DAYS - 1:
                ex_min = 0
            burn = int(round(_lerp(arc["burn"][0], arc["burn"][1], t) + _jit(i, 40))) if ex_min else 0
            intake = int(round(_lerp(arc["intake"][0], arc["intake"][1], t) + _jit(i, 80)))
            protein = int(round(_lerp(arc["protein"][0], arc["protein"][1], t) + _jit(i, 6)))
            balance = round(max(0, min(100, _lerp(arc["balance"][0], arc["balance"][1], t) + _jit(i, 4))), 1)
            total_hours = round(max(5.0, sleep_score / 12.0 + 1.0), 1)
            deep_pct = int(round(max(8, min(28, sleep_score / 4))))
            rpe = int(round(_lerp(arc["rpe"][0], arc["rpe"][1], t)))

            # watch_data
            cur.execute(
                """
                INSERT INTO watch_data
                    (user_id, date, steps, exercise_minutes, calories_burned,
                     heart_rate_avg, heart_rate_rest, heart_rate_max,
                     hrv_data, sleep_data, stress_level, blood_oxygen)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (uid, d, steps, ex_min, burn,
                 rhr + 14, rhr, rhr + (90 if ex_min else 40),
                 Json({"rmssd": hrv, "sdnn": round(hrv * 1.2, 1), "lf_hf_ratio": round(1.0 + (70 - rhr) / 50, 2)}),
                 Json({"sleep_score": sleep_score, "total_hours": total_hours,
                       "deep_sleep_percent": deep_pct, "rem_sleep_percent": 22,
                       "stages_timeline": _sleep_stages_timeline(total_hours, deep_pct)}),
                 int(max(10, min(90, 100 - sleep_score + (rpe * 4)))), 97 if arc_name == "improving" else 95),
            )

            # exercise_records（训练日才有）
            if ex_min:
                peak = rhr + (95 if arc_name == "degrading" else 80)
                hr60 = peak - (12 if arc_name == "degrading" else 22)  # 恶化:HRR低
                cur.execute(
                    """
                    INSERT INTO exercise_records (user_id, date, exercise_type, analysis_result, form_quality)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (uid, d, "力量+有氧" if arc_name == "improving" else "大重量深蹲",
                     Json({"duration_minutes": ex_min, "peak_hr": peak, "hr_60s": hr60, "rpe": rpe,
                           "calories": burn}),
                     "good" if arc_name == "improving" else "fair"),
                )

            # nutrition_logs
            carbs = int(round(intake * 0.45 / 4))
            fat = int(round(intake * 0.27 / 9))
            cur.execute(
                """
                INSERT INTO nutrition_logs (user_id, date, meal_type, nutrition_result, balance_score)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (uid, d, "daily",
                 Json({"total_calories": intake, "protein_g": protein, "carbs_g": carbs, "fat_g": fat,
                       "diet_narrative": diet_pool[i % len(diet_pool)]}),
                 balance),
            )
            last = {"weight": _lerp(arc["weight"][0], arc["weight"][1], t),
                    "body_fat": _lerp(arc["body_fat"][0], arc["body_fat"][1], t),
                    "muscle": _lerp(arc["muscle"][0], arc["muscle"][1], t)}

        # users：当前体测 + 目标
        cur.execute(
            """
            UPDATE users SET weight_kg=%s, body_fat_pct=%s, muscle_mass_kg=%s,
                             goals=%s, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            (round(last["weight"], 1), round(last["body_fat"], 1), round(last["muscle"], 1),
             Json(GOALS), uid),
        )
    print(f"  user={uid} arc={arc_name}: 已写入 {DAYS} 天 watch/exercise/nutrition + users 体测目标")


def ensure_ddl(conn):
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS muscle_mass_kg FLOAT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS body_fat_pct FLOAT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS goals JSONB")


def ensure_user(conn, uid, name, age, gender, height, weight):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (id, name, age, gender, height_cm, weight_kg, fitness_level, goal, activity_level)
            VALUES (%s,%s,%s,%s,%s,%s,'intermediate','lose_weight','moderate')
            ON CONFLICT (id) DO NOTHING
            """,
            (uid, name, age, gender, height, weight),
        )


def main():
    params = get_connection_params()
    conn = psycopg2.connect(**params)
    try:
        ensure_ddl(conn)
        ensure_user(conn, 1, "小明", 30, "male", 175, 72)
        ensure_user(conn, 2, "小强(恶化对照)", 30, "male", 178, 80)
        print("开始造数据（最近 %d 天）..." % DAYS)
        seed_week(conn, 1, "improving")
        seed_week(conn, 2, "degrading")
        conn.commit()
        print("✅ 完成。user=1 向好周；user=2 恶化周。")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
