"""
「暴汗艺术家」健康智能体 - 工具层（确定性公式 + 外部 API mock）

设计原则（对应设计方案"数据接入层：拒绝 AI 盲目口算"）：
- 所有核心生理指标（RS / HRR / TRIMP / 疲劳红旗）一律用**硬编码 Python 公式**计算，
  绝不交给大模型口算，保证数字可复现、可审计。
- 外部数据源（wger 动作库、USDA 食物库）本期先用**本地 mock**，
  函数签名与设计方案一致，后续可无缝替换为真实 HTTP 调用。

适用于大模型技术初级用户：
- "确定性工具" = 普通 Python 函数，输入输出固定，不含随机性，便于单元测试。
- "@tool 装饰器" 把函数注册为 LangChain 工具，让智能体能够 Function Calling 调用。
"""

from __future__ import annotations

import math
from typing import Dict, List, Any

from langchain_core.tools import tool


# =============================================================================
# 一、确定性生理公式（硬编码，禁止 LLM 口算）
# =============================================================================

# 基线缺省值：当数据库历史样本不足以计算个人基线时使用。
DEFAULT_HRV_BASELINE = 45.0   # ms，健康成年人 RMSSD 参考基线
DEFAULT_RHR_BASELINE = 60     # bpm，静息心率参考基线

# 油脂代偿系数：检测到"沙拉/油炸/酱料"等描述时，对食材基准热量放大，防止热量低估。
LAMBDA_SAUCE = 1.30
SAUCE_KEYWORDS = ["沙拉", "油炸", "炸", "酱", "红烧", "盖饭", "啤酒", "宵夜", "方便面", "甜"]


def calc_readiness_score(
    hrv_today: float,
    sleep_score: float,
    rhr_today: float,
    hrv_baseline: float = DEFAULT_HRV_BASELINE,
    rhr_baseline: float = DEFAULT_RHR_BASELINE,
) -> float:
    """计算生理准备度指数 Readiness Score（百分制）。

    公式（设计方案 §4.2①）：
        RS = 0.5 * (今日HRV / HRV基准)
           + 0.3 * (睡眠评分 / 100)
           + 0.2 * (基线RHR / 今日RHR)
    再折算为百分制，并裁剪到 [0, 100]。
    """
    if hrv_baseline <= 0:
        hrv_baseline = DEFAULT_HRV_BASELINE
    if rhr_today <= 0:
        rhr_today = DEFAULT_RHR_BASELINE

    rs_raw = (
        0.5 * (hrv_today / hrv_baseline)
        + 0.3 * (sleep_score / 100.0)
        + 0.2 * (rhr_baseline / rhr_today)
    )
    rs = rs_raw * 100.0
    return round(max(0.0, min(100.0, rs)), 1)


def calc_hrr(peak_hr: int, hr_60s: int) -> int:
    """计算心率恢复力 HRR = 运动峰值心率 - 运动后 60 秒心率。

    HRR 越大越好，<18bpm 提示副交感神经恢复差（设计方案健康标准）。
    """
    return int(peak_hr) - int(hr_60s)


def calc_trimp(duration_minutes: int, rpe: int) -> int:
    """计算训练冲量 TRIMP（采用 session-RPE 法）。

    TRIMP = 训练时长(min) × 主观疲劳度 RPE(1-10)
    例：90min × RPE9 = 810（过度训练）；30min × RPE4 = 120（主动恢复）。
    """
    return int(duration_minutes) * int(rpe)


def calc_fatigue_flags(
    hrv_today: float,
    sleep_score: float,
    hrr: int,
    rhr_trend_up_3d: bool,
    hrv_baseline: float = DEFAULT_HRV_BASELINE,
) -> Dict[str, Any]:
    """评估系统疲劳红旗，命中一项 +1（设计方案 §4.2① Step2）。

    检查四项：
      1. HRV 低于基线 80%
      2. 睡眠评分 < 70
      3. HRR < 18 bpm
      4. 静息心率连续 3 天升高

    返回：{count, flags, fatigue} —— fatigue ∈ {low, medium, high}
    """
    flags: List[str] = []
    if hrv_baseline <= 0:
        hrv_baseline = DEFAULT_HRV_BASELINE

    if hrv_today < 0.8 * hrv_baseline:
        flags.append(f"HRV {hrv_today}ms 低于基线80%({round(0.8 * hrv_baseline, 1)}ms)")
    if sleep_score < 70:
        flags.append(f"睡眠评分 {sleep_score} < 70")
    if hrr < 18:
        flags.append(f"HRR {hrr}bpm < 18bpm")
    if rhr_trend_up_3d:
        flags.append("静息心率连续3天升高")

    count = len(flags)
    if count == 0:
        fatigue = "low"
    elif count <= 2:
        fatigue = "medium"
    else:
        fatigue = "high"

    return {"count": count, "flags": flags, "fatigue": fatigue}


def calc_body_age(
    resting_hr: int,
    bmi: float,
    exercise_frequency: int,
    sleep_quality: float,
    chronological_age: int = 30,
) -> float:
    """多因子非线性补偿身体年龄模型（在实际年龄基础上加减偏移）。"""
    base = float(chronological_age)
    hr_score = -3 if resting_hr < 60 else (0 if resting_hr < 70 else (3 if resting_hr < 80 else 5))
    bmi_score = 0 if 18.5 <= bmi < 24 else (3 if bmi < 28 else 6)
    freq_score = -3 if exercise_frequency >= 5 else (-1 if exercise_frequency >= 3 else 1)
    sleep_score_adj = -2 if sleep_quality >= 8 else (0 if sleep_quality >= 6 else 3)
    age = base + hr_score + bmi_score + freq_score + sleep_score_adj
    return round(max(18.0, min(80.0, age)), 1)


def calc_bmi(weight_kg: float, height_cm: float) -> float:
    """身体质量指数 BMI = 体重(kg) / 身高(m)²。"""
    if height_cm <= 0:
        return 0.0
    h = height_cm / 100.0
    return round(weight_kg / (h * h), 1)


def calc_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> int:
    """基础代谢率 BMR（Mifflin-St Jeor 公式）。"""
    if str(gender).lower().startswith("m") or gender in ("男", "male"):
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return int(bmr)


_ACTIVITY_MULT = {
    "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
    "active": 1.725, "very_active": 1.9,
}


def calc_tdee(bmr: int, activity_level: str = "moderate") -> int:
    """每日总能量消耗 TDEE = BMR × 活动系数。"""
    return int(bmr * _ACTIVITY_MULT.get(activity_level, 1.55))


def detect_sauce(diet_narrative: str) -> bool:
    """检测饮食描述中是否含隐形高油脂/高热量信号（触发油脂代偿）。"""
    text = diet_narrative or ""
    return any(kw in text for kw in SAUCE_KEYWORDS)


# =============================================================================
# 二、外部数据源 mock（wger 动作库 / USDA 食物库）
#     函数签名与设计方案一致，后续可替换为真实 HTTP 调用。
# =============================================================================

# wger 动作库（mock）：含处方(组数/次数/时长)，便于前端渲染"4组×12次 / 5分钟"
# prescription: {sets, reps}=力量类 ; {sets, duration_sec}=拉伸/恢复类
EXERCISE_LIBRARY: Dict[str, Dict[str, Any]] = {
    # —— 低负荷恢复类 ——
    "core stretch": {"name": "核心拉伸 (Core Stretch)", "muscles": ["核心", "脊柱"], "load": "low",
                      "description": "仰卧/四点支撑下进行脊柱中立位拉伸，激活腹横肌",
                      "prescription": {"sets": 3, "duration_sec": 30}},
    "mobility": {"name": "关节灵活性训练 (Mobility)", "muscles": ["髋", "胸椎"], "load": "low",
                  "description": "动态髋关节绕环与胸椎旋转，改善活动度",
                  "prescription": {"sets": 2, "duration_sec": 60}},
    "cat cow": {"name": "猫牛式 (Cat-Cow)", "muscles": ["脊柱", "核心"], "load": "low",
                 "description": "四点支撑，呼吸配合交替拱背凹背，松动脊柱",
                 "prescription": {"sets": 3, "reps": 12}},
    "dead bug": {"name": "死虫式 (Dead Bug)", "muscles": ["核心", "腹横肌"], "load": "low",
                  "description": "仰卧，对侧手脚交替伸展，维持腰椎稳定",
                  "prescription": {"sets": 3, "reps": 10}},
    "box squat": {"name": "徒手箱式深蹲 (Box Squat)", "muscles": ["股四头肌", "臀大肌"], "load": "low",
                   "description": "蹲至箱子高度控制离心，降低腰椎剪切负荷",
                   "prescription": {"sets": 3, "reps": 12}},
    # —— 中高强度力量类（维持/进阶路径用）——
    "squat": {"name": "深蹲 (Squat)", "muscles": ["股四头肌", "臀大肌"], "load": "high",
               "description": "杠铃/徒手深蹲，屈髋屈膝至大腿平行", "prescription": {"sets": 4, "reps": 12}},
    "push up": {"name": "俯卧撑 (Push-up)", "muscles": ["胸大肌", "三头肌"], "load": "medium",
                 "description": "俯身屈臂下放至胸近地面再推起", "prescription": {"sets": 4, "reps": 12}},
    "deadlift": {"name": "硬拉 (Deadlift)", "muscles": ["臀大肌", "竖脊肌", "腘绳肌"], "load": "high",
                  "description": "髋铰链发力将杠铃拉起，保持脊柱中立", "prescription": {"sets": 4, "reps": 10}},
    "plank": {"name": "平板支撑 (Plank)", "muscles": ["核心"], "load": "medium",
               "description": "肘撑地面维持躯干一条直线", "prescription": {"sets": 3, "duration_sec": 45}},
}

_DEFAULT_RECOVERY = ["cat cow", "dead bug", "core stretch"]
_STRENGTH_PLAN = ["squat", "push up", "deadlift", "plank"]


@tool
def wger_exercise_search(query: str = "stretch", limit: int = 3) -> Dict[str, Any]:
    """从 wger 动作库检索训练动作（含组数/次数/时长处方）。

    Args:
        query: 检索关键词，如 "core stretch" / "mobility" / "strength"。
        limit: 返回动作数量上限。

    Returns:
        {"source": "wger_api", "query": ..., "exercises": [{name, muscles, prescription, ...}]}
    """
    q = (query or "").lower()
    if "strength" in q or "力量" in q or "维持" in q or "maintain" in q:
        matched = [EXERCISE_LIBRARY[k] for k in _STRENGTH_PLAN]
    else:
        matched = [v for k, v in EXERCISE_LIBRARY.items() if k in q or q in k]
        if not matched:
            matched = [EXERCISE_LIBRARY[k] for k in _DEFAULT_RECOVERY]
    return {"source": "wger_api", "query": query, "exercises": matched[: max(1, limit)]}


# —— 结构化餐单模板（餐别×食材×克数），单品热量由 FOOD_DATABASE 实算 ——
_MEAL_TEMPLATES = [
    {"meal": "早餐", "time": "08:30", "items": [("鸡蛋", 100), ("希腊酸奶", 150), ("蓝莓", 50)]},
    {"meal": "午餐", "time": "12:30", "items": [("鸡胸肉", 150), ("糙米饭", 120), ("西兰花", 100)]},
    {"meal": "晚餐", "time": "18:30", "items": [("三文鱼", 150), ("藜麦", 80), ("西兰花", 100)]},
]


def build_meal_plan(sauce_factor: float = 1.0) -> Dict[str, Any]:
    """基于 USDA 食物库组装结构化三餐（餐别/食材/克数/单品热量/蛋白）。

    Args:
        sauce_factor: 油脂代偿系数（检测到酱料时传 LAMBDA_SAUCE）。
    Returns: {"meals": [...], "day_total_calories": int, "day_total_protein": int}
    """
    meals = []
    day_cal = day_pro = 0.0
    for tpl in _MEAL_TEMPLATES:
        foods = []
        meal_cal = 0.0
        for name, grams in tpl["items"]:
            db = FOOD_DATABASE.get(name, {})
            factor = grams / 100.0
            cal = round(db.get("calories", 0) * factor * sauce_factor)
            pro = round(db.get("protein", 0) * factor, 1)
            foods.append({"name": name, "grams": grams, "calories": cal, "protein": pro})
            meal_cal += cal
            day_pro += pro
        day_cal += meal_cal
        meals.append({"meal": tpl["meal"], "time": tpl["time"],
                      "total_calories": int(meal_cal), "foods": foods})
    return {"meals": meals, "day_total_calories": int(day_cal), "day_total_protein": int(round(day_pro))}


# USDA 食物库（mock）：每 100g 营养（kcal / 蛋白g / 碳水g / 脂肪g）
FOOD_DATABASE: Dict[str, Dict[str, Any]] = {
    "三文鱼": {"calories": 208, "protein": 20.0, "carbs": 0.0, "fat": 13.0},
    "salmon": {"calories": 208, "protein": 20.0, "carbs": 0.0, "fat": 13.0},
    "鸡胸肉": {"calories": 133, "protein": 31.0, "carbs": 0.0, "fat": 1.2},
    "糙米饭": {"calories": 123, "protein": 2.6, "carbs": 25.6, "fat": 0.9},
    "藜麦": {"calories": 120, "protein": 4.4, "carbs": 21.3, "fat": 1.9},
    "西兰花": {"calories": 34, "protein": 2.8, "carbs": 6.6, "fat": 0.4},
    "希腊酸奶": {"calories": 59, "protein": 10.0, "carbs": 3.6, "fat": 0.4},
    "鸡蛋": {"calories": 155, "protein": 13.0, "carbs": 1.1, "fat": 11.0},
    "蓝莓": {"calories": 57, "protein": 0.7, "carbs": 14.5, "fat": 0.3},
}


@tool
def usda_food_search(keyword: str) -> Dict[str, Any]:
    """查询 USDA 食物营养数据库，获取单一食材的营养成分（每 100g）。

    Args:
        keyword: 食材名称，如 "salmon" / "三文鱼"。

    Returns:
        命中：{"source": "usda_api", "food": ..., "calories": ..., "protein": ..., ...}
        未命中：{"source": "usda_api", "food": ..., "status": "not_found"}
    """
    key = (keyword or "").strip()
    data = FOOD_DATABASE.get(key)
    if data is None:
        # 宽松匹配（包含关系）
        for name, v in FOOD_DATABASE.items():
            if name in key or key in name:
                data = v
                break
    if data:
        return {"source": "usda_api", "food": keyword, "per": "100g", **data}
    return {"source": "usda_api", "food": keyword, "status": "not_found"}


# 工具注册表：供编排层 / 未来 bind_tools 使用
TOOL_REGISTRY = {
    "wger_exercise_search": wger_exercise_search,
    "usda_food_search": usda_food_search,
}
