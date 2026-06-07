"""
LangGraph多Agent状态机实现
核心编排层，管理多个专业Agent的协作
"""

import os
import re
import json
import time
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from dataclasses import dataclass, field

from .state import AgentState, AgentRole, HealthMetrics, ExerciseAnalysis, NutritionAnalysis, SafetyResult, AgentDecision


# =============================================================================
# 工具函数定义 (Tools)
# =============================================================================

class ToolRegistry:
    """工具注册中心"""
    
    TOOLS = {
        # ========== 计算工具 ==========
        "calculate_bmi": {
            "name": "calculate_bmi",
            "description": "计算身体质量指数BMI",
            "parameters": {
                "weight_kg": {"type": "number", "description": "体重(kg)"},
                "height_cm": {"type": "number", "description": "身高(cm)"}
            },
            "category": "calculator"
        },
        "calculate_bmr": {
            "name": "calculate_bmr",
            "description": "计算基础代谢率(Mifflin-St Jeor公式)",
            "parameters": {
                "weight_kg": {"type": "number"},
                "height_cm": {"type": "number"},
                "age": {"type": "integer"},
                "gender": {"type": "string", "enum": ["male", "female"]}
            },
            "category": "calculator"
        },
        "calculate_tdee": {
            "name": "calculate_tdee",
            "description": "计算每日总能量消耗",
            "parameters": {
                "bmr": {"type": "number"},
                "activity_level": {"type": "string", "enum": ["sedentary", "light", "moderate", "active", "very_active"]}
            },
            "category": "calculator"
        },
        "calculate_body_age": {
            "name": "calculate_body_age",
            "description": "估算身体年龄",
            "parameters": {
                "resting_heart_rate": {"type": "integer"},
                "bmi": {"type": "number"},
                "exercise_frequency": {"type": "integer"},
                "sleep_quality": {"type": "number"}
            },
            "category": "calculator"
        },
        "calculate_recovery_score": {
            "name": "calculate_recovery_score",
            "description": "计算身体准备度指数(Recovery Score)",
            "parameters": {
                "sleep_hours": {"type": "number"},
                "sleep_quality": {"type": "number"},
                "resting_hr": {"type": "integer"},
                "hrv_data": {"type": "object", "description": "心率变异性数据"}
            },
            "category": "calculator"
        },
        
        # ========== 营养工具 (USDA API) ==========
        "retrieve_usda_nutrients": {
            "name": "retrieve_usda_nutrients",
            "description": "查询USDA食物营养数据库，获取食物营养成分",
            "parameters": {
                "food_name": {"type": "string", "description": "食物名称"}
            },
            "api": "USDA FoodData Central",
            "category": "nutrition"
        },
        "calculate_meal_macros": {
            "name": "calculate_meal_macros",
            "description": "计算餐食宏量营养素",
            "parameters": {
                "foods": {"type": "array", "description": "食物列表[{name, grams}]"}
            },
            "category": "nutrition"
        },
        
        # ========== 训练工具 (wger API) ==========
        "fetch_wger_exercise": {
            "name": "fetch_wger_exercise",
            "description": "从wger动作库获取标准运动动作描述",
            "parameters": {
                "exercise_name": {"type": "string"}
            },
            "api": "wger.de Workout Manager",
            "category": "training"
        },
        "fetch_corrective_exercise": {
            "name": "fetch_corrective_exercise",
            "description": "获取代偿修正训练动作",
            "parameters": {
                "issue": {"type": "string", "description": "问题类型(塌腰/耸肩等)"}
            },
            "category": "training"
        },
        
        # ========== 睡眠分析 ==========
        "analyze_sleep_quality": {
            "name": "analyze_sleep_quality",
            "description": "分析睡眠质量",
            "parameters": {
                "sleep_hours": {"type": "number"},
                "deep_sleep_percent": {"type": "number"},
                "rem_sleep_percent": {"type": "number"}
            },
            "category": "sleep"
        },
    }
    
    @classmethod
    def get_tool_schemas(cls) -> List[Dict]:
        """获取所有工具的模式定义"""
        return list(cls.TOOLS.values())
    
    @classmethod
    def get_tools_by_category(cls, category: str) -> List[Dict]:
        return [t for t in cls.TOOLS.values() if t.get("category") == category]


# =============================================================================
# 工具执行函数
# =============================================================================

def execute_tool(tool_name: str, arguments: Dict) -> Dict:
    """
    执行工具函数
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
        
    Returns:
        执行结果
    """
    tool_funcs = {
        # 计算工具
        "calculate_bmi": _calc_bmi,
        "calculate_bmr": _calc_bmr,
        "calculate_tdee": _calc_tdee,
        "calculate_body_age": _calc_body_age,
        "calculate_recovery_score": _calc_recovery_score,
        
        # 营养工具
        "retrieve_usda_nutrients": _usda_lookup,
        "calculate_meal_macros": _calc_meal_macros,
        
        # 训练工具
        "fetch_wger_exercise": _wger_lookup,
        "fetch_corrective_exercise": _get_corrective,
        
        # 睡眠工具
        "analyze_sleep_quality": _analyze_sleep,
    }
    
    func = tool_funcs.get(tool_name)
    if func:
        return func(arguments)
    return {"error": f"Unknown tool: {tool_name}"}


def _calc_bmi(args: Dict) -> Dict:
    weight, height = args["weight_kg"], args["height_cm"]
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    return {"bmi": round(bmi, 1), "category": _bmi_category(bmi)}


def _bmi_category(bmi: float) -> str:
    if bmi < 18.5: return "偏瘦"
    if bmi < 24: return "正常"
    if bmi < 28: return "超重"
    return "肥胖"


def _calc_bmr(args: Dict) -> Dict:
    w, h, age, gender = args["weight_kg"], args["height_cm"], args["age"], args["gender"]
    if gender == "male":
        bmr = 10 * w + 6.25 * h - 5 * age + 5
    else:
        bmr = 10 * w + 6.25 * h - 5 * age - 161
    return {"bmr": int(bmr)}


def _calc_tdee(args: Dict) -> Dict:
    multipliers = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
    mult = multipliers.get(args["activity_level"], 1.55)
    tdee = args["bmr"] * mult
    return {"tdee": int(tdee)}


def _calc_body_age(args: Dict) -> Dict:
    hr, bmi, freq, sleep = args["resting_heart_rate"], args["bmi"], args["exercise_frequency"], args["sleep_quality"]
    base = 30
    hr_score = -5 if hr < 60 else (-3 if hr < 70 else (0 if hr < 80 else 3))
    bmi_score = 0 if 18.5 <= bmi < 24 else (3 if bmi < 28 else 6)
    freq_score = -5 if freq >= 5 else (-3 if freq >= 3 else 0)
    sleep_score = -2 if sleep >= 8 else (0 if sleep >= 6 else 3)
    age = base + hr_score + bmi_score + freq_score + sleep_score
    return {"body_age": max(18, min(80, int(age)))}


def _calc_recovery_score(args: Dict) -> Dict:
    sleep_h, sleep_q, hr = args["sleep_hours"], args["sleep_quality"], args["resting_hr"]
    score = (sleep_h / 8 * 40) + (sleep_q / 10 * 30) + ((180 - hr) / 60 * 30)
    return {"recovery_score": round(score, 1), "status": "high" if score > 70 else ("medium" if score > 50 else "low")}


# USDA营养数据库 (模拟)
FOOD_DATABASE = {
    "鸡胸肉": {"calories": 133, "protein": 31, "carbs": 0, "fat": 1.2, "per": "100g"},
    "三文鱼": {"calories": 208, "protein": 20, "carbs": 0, "fat": 13, "per": "100g"},
    "米饭": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3, "per": "100g"},
    "西兰花": {"calories": 34, "protein": 2.8, "carbs": 6.6, "fat": 0.4, "per": "100g"},
    "鸡蛋": {"calories": 155, "protein": 13, "carbs": 1.1, "fat": 11, "per": "100g"},
    "牛奶": {"calories": 54, "protein": 3, "carbs": 5, "fat": 3.2, "per": "100ml"},
    "香蕉": {"calories": 93, "protein": 1.4, "carbs": 23, "fat": 0.2, "per": "100g"},
    "苹果": {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2, "per": "100g"},
}

def _usda_lookup(args: Dict) -> Dict:
    food = args["food_name"]
    data = FOOD_DATABASE.get(food, {})
    if data:
        return {"food": food, "source": "USDA FoodData Central", **data}
    return {"food": food, "source": "USDA FoodData Central", "status": "not_found"}


def _calc_meal_macros(args: Dict) -> Dict:
    foods = args.get("foods", [])
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for item in foods:
        name, grams = item.get("name", ""), item.get("grams", 100)
        data = FOOD_DATABASE.get(name, {})
        factor = grams / 100
        total["calories"] += data.get("calories", 0) * factor
        total["protein"] += data.get("protein", 0) * factor
        total["carbs"] += data.get("carbs", 0) * factor
        total["fat"] += data.get("fat", 0) * factor
    return {k: round(v, 1) for k, v in total.items()}


# wger动作库 (模拟)
EXERCISE_LIBRARY = {
    "深蹲": {"name": "深蹲", "muscles": ["股四头肌", "臀大肌", "腿后肌"], "description": "双脚与肩同宽，屈髋屈膝下蹲", "api": "wger.de"},
    "箱式深蹲": {"name": "箱式深蹲", "muscles": ["股四头肌", "臀大肌"], "description": "蹲至箱子高度，控制下蹲速度", "api": "wger.de"},
    "猫牛式": {"name": "猫牛式", "muscles": ["脊柱", "核心"], "description": "四点支撑，交替拱背凹背", "api": "wger.de"},
    "死虫式": {"name": "死虫式", "muscles": ["核心", "腹横肌"], "description": "仰卧，对侧手脚交替伸展", "api": "wger.de"},
}

def _wger_lookup(args: Dict) -> Dict:
    name = args["exercise_name"]
    data = EXERCISE_LIBRARY.get(name, {})
    if data:
        return {"source": "wger.de Workout API", **data}
    return {"exercise": name, "source": "wger.de", "status": "not_found"}


CORRECTIVE_EXERCISES = {
    "塌腰": ["猫牛式", "死虫式", "平板支撑"],
    "耸肩": ["肩部拉伸", "弹力带肩外旋", "泡沫轴放松"],
    "膝盖内扣": ["侧卧抬腿", "蚌式开合", "臀中肌训练"],
}

def _get_corrective(args: Dict) -> Dict:
    issue = args["issue"]
    exercises = CORRECTIVE_EXERCISES.get(issue, ["全身拉伸"])
    return {"issue": issue, "corrective_exercises": exercises, "source": "wger.de"}


def _analyze_sleep(args: Dict) -> Dict:
    hours, deep, rem = args["sleep_hours"], args["deep_sleep_percent"], args.get("rem_sleep_percent", 22)
    score = 50
    if 7 <= hours <= 9: score += 25
    elif 6 <= hours < 7 or 9 < hours <= 10: score += 15
    if 15 <= deep <= 25: score += 15
    if 20 <= rem <= 25: score += 10
    return {"sleep_score": min(100, score), "quality": "excellent" if score > 85 else ("good" if score > 70 else "fair")}


# =============================================================================
# Agent节点定义
# =============================================================================

class AgentNode:
    """Agent节点基类"""
    
    def __init__(self, name: str, role: AgentRole, description: str):
        self.name = name
        self.role = role
        self.description = description
        self.tools = []
        self.prompt = ""
    
    def process(self, state: AgentState) -> AgentState:
        raise NotImplementedError
    
    def call_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """执行工具调用"""
        results = []
        for call in tool_calls:
            tool_name = call.get("name")
            arguments = call.get("arguments", {})
            start = time.time()
            result = execute_tool(tool_name, arguments)
            elapsed = (time.time() - start) * 1000
            results.append({
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
                "success": "error" not in result,
                "execution_time_ms": round(elapsed, 2),
                "api_source": ToolRegistry.TOOLS.get(tool_name, {}).get("api", "internal")
            })
        return results


class StateEvaluator(AgentNode):
    """状态评估器 - 评估用户当前生理状态"""
    
    def __init__(self):
        super().__init__(
            name="Dr. Physio",
            role=AgentRole.STATE_EVALUATOR,
            description="评估用户身体准备度和恢复状态"
        )
        self.tools = ["calculate_bmi", "calculate_bmr", "calculate_tdee", "calculate_body_age", "calculate_recovery_score"]
    
    def process(self, state: AgentState) -> AgentState:
        watch_data = state.get("watch_data", {})
        if not watch_data:
            state["error"] = "缺少手表数据"
            return state
        
        # 模拟LLM推理 - 调用工具
        tool_calls = [
            {"name": "calculate_bmi", "arguments": {"weight_kg": 72, "height_cm": 175}},
            {"name": "calculate_bmr", "arguments": {"weight_kg": 72, "height_cm": 175, "age": 28, "gender": "male"}},
            {"name": "calculate_tdee", "arguments": {"bmr": 1680, "activity_level": "moderate"}},
            {"name": "calculate_body_age", "arguments": {"resting_heart_rate": 65, "bmi": 23.5, "exercise_frequency": 4, "sleep_quality": 8}},
            {"name": "calculate_recovery_score", "arguments": {"sleep_hours": 7.5, "sleep_quality": 8, "resting_hr": 65, "hrv_data": {}}},
        ]
        
        tool_results = self.call_tools(tool_calls)
        
        # 解析结果
        metrics = HealthMetrics()
        for res in tool_results:
            if res["tool"] == "calculate_bmi":
                metrics.bmi = res["result"]["bmi"]
            elif res["tool"] == "calculate_bmr":
                metrics.bmr = res["result"]["bmr"]
            elif res["tool"] == "calculate_tdee":
                metrics.tdee = res["result"]["tdee"]
            elif res["tool"] == "calculate_body_age":
                metrics.body_age = res["result"]["body_age"]
            elif res["tool"] == "calculate_recovery_score":
                metrics_dict = res["result"]
        
        state["health_metrics"] = metrics
        state["current_agent"] = AgentRole.STATE_EVALUATOR
        state["reasoning_chain"].append(
            f"[StateEvaluator] 分析手表数据，计算BMI={metrics.bmi}, BMR={metrics.bmr}, TDEE={metrics.tdee}, 身体年龄={metrics.body_age}"
        )
        
        # 记录决策
        state["decision_history"].append({
            "agent": self.name,
            "role": self.role.value,
            "timestamp": datetime.now().isoformat(),
            "tools_used": [r["tool"] for r in tool_results],
            "reasoning": "基于手表数据计算基本生理指标"
        })
        
        state["step"] = state.get("step", 0) + 1
        return state


class ExerciseCoach(AgentNode):
    """训练教练 - 分析运动动作并提供指导"""
    
    def __init__(self):
        super().__init__(
            name="Coach Alex",
            role=AgentRole.EXERCISE_COACH,
            description="分析运动动作质量，制定训练计划"
        )
        self.tools = ["fetch_wger_exercise", "fetch_corrective_exercise"]
    
    def process(self, state: AgentState) -> AgentState:
        exercise_analysis = state.get("exercise_analysis")
        
        if exercise_analysis and exercise_analysis.form_quality != "unknown":
            # 已有视频分析结果
            warnings = exercise_analysis.warnings
            if warnings:
                # 需要修正动作
                tool_result = self.call_tools([
                    {"name": "fetch_corrective_exercise", "arguments": {"issue": "塌腰"}}
                ])
                state["reasoning_chain"].append(
                    f"[ExerciseCoach] 检测到动作问题，获取修正动作: {tool_result[0]['result']}"
                )
        else:
            # 没有视频数据，基于健康指标推荐
            health_metrics = state.get("health_metrics")
            if health_metrics:
                body_age = health_metrics.body_age
                bmi = health_metrics.bmi
                
                if bmi > 25:
                    focus = "减脂"
                    exercise_type = "有氧+力量"
                elif bmi < 18.5:
                    focus = "增肌"
                    exercise_type = "力量训练为主"
                else:
                    focus = "维持+提升"
                    exercise_type = "综合训练"
                
                state["training_plan"] = {
                    "focus": focus,
                    "type": exercise_type,
                    "suggested_exercises": ["深蹲", "卧推", "硬拉", "划船"]
                }
                
                state["reasoning_chain"].append(
                    f"[ExerciseCoach] 基于BMI={bmi}、身体年龄={body_age}，推荐{focus}训练"
                )
        
        state["current_agent"] = AgentRole.EXERCISE_COACH
        state["step"] = state.get("step", 0) + 1
        return state


class NutritionPlanner(AgentNode):
    """营养规划师 - 计算营养需求和饮食计划"""
    
    def __init__(self):
        super().__init__(
            name="NutriBot",
            role=AgentRole.NUTRITION_PLANNER,
            description="规划营养摄入，调用USDA数据"
        )
        self.tools = ["retrieve_usda_nutrients", "calculate_meal_macros"]
    
    def process(self, state: AgentState) -> AgentState:
        health_metrics = state.get("health_metrics")
        nutrition_analysis = state.get("nutrition_analysis")
        
        if not health_metrics:
            state["error"] = "缺少健康指标数据"
            return state
        
        tdee = health_metrics.tdee
        
        # 计算目标热量 (减脂: 0.8*TDEE, 增肌: 1.1*TDEE)
        target_calories = int(tdee * 0.85)
        
        # 计算宏量营养素
        protein_g = int(target_calories * 0.30 / 4)  # 30%蛋白
        carbs_g = int(target_calories * 0.40 / 4)   # 40%碳水
        fat_g = int(target_calories * 0.30 / 9)    # 30%脂肪
        
        # 调用USDA获取食物数据
        tool_results = self.call_tools([
            {"name": "retrieve_usda_nutrients", "arguments": {"food_name": "鸡胸肉"}},
            {"name": "retrieve_usda_nutrients", "arguments": {"food_name": "西兰花"}},
            {"name": "retrieve_usda_nutrients", "arguments": {"food_name": "米饭"}},
        ])
        
        # 构建饮食计划
        meal_plan = {
            "target_calories": target_calories,
            "macros": {
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g
            },
            "meals": {
                "breakfast": {"foods": ["鸡蛋", "牛奶", "香蕉"], "calories": 450},
                "lunch": {"foods": ["鸡胸肉", "米饭", "西兰花"], "calories": 650},
                "dinner": {"foods": ["三文鱼", "蔬菜"], "calories": 500}
            },
            "usda_data": [r["result"] for r in tool_results]
        }
        
        state["meal_plan"] = meal_plan
        state["current_agent"] = AgentRole.NUTRITION_PLANNER
        state["reasoning_chain"].append(
            f"[NutritionPlanner] 目标热量={target_calories}kcal, 宏量: P={protein_g}g C={carbs_g}g F={fat_g}g"
        )
        state["reasoning_chain"].append(f"[NutritionPlanner] 调用USDA获取食物营养数据")
        
        state["decision_history"].append({
            "agent": self.name,
            "role": self.role.value,
            "timestamp": datetime.now().isoformat(),
            "tools_used": ["retrieve_usda_nutrients"] * 3,
            "api_calls": [r["result"] for r in tool_results]
        })
        
        state["step"] = state.get("step", 0) + 1
        return state


class GuardrailAuditor(AgentNode):
    """安全审计员 - 检查越狱和不当内容"""
    
    def __init__(self):
        super().__init__(
            name="SafetyShield",
            role=AgentRole.GUARDRAIL_AUDITOR,
            description="审核所有输出，确保安全合规"
        )
        # 注入检测模式
        self.injection_patterns = [
            r"ignore\s+(previous|all)",
            r"disregard\s+your",
            r"you\s+are\s+now",
            r"忽略.*之前",
            r"你现在?是",
            r"打破.*角色",
        ]
        # 医疗禁区
        self.medical_forbidden = [
            "诊断", "治疗", "治愈", "处方", "开药",
            "睾酮", "类固醇", "双氯芬酸", "处方药",
        ]
    
    def process(self, state: AgentState) -> AgentState:
        recommendations = state.get("recommendations", [])
        
        violations = []
        warnings = []
        
        for rec in recommendations:
            rec_text = str(rec)
            
            # 检查注入
            for pattern in self.injection_patterns:
                if re.search(pattern, rec_text, re.IGNORECASE):
                    violations.append(f"检测到提示注入模式: {pattern}")
            
            # 检查医疗禁区
            for term in self.medical_forbidden:
                if term in rec_text:
                    violations.append(f"包含医疗禁区词汇: {term}")
        
        safety_result = SafetyResult()
        if violations:
            safety_result.is_safe = False
            safety_result.violations = violations
            safety_result.拦截类别 = "medical" if any(v in str(self.medical_forbidden) for v in violations) else "injection"
        
        state["safety_result"] = safety_result
        state["guardrail_active"] = not safety_result.is_safe
        state["current_agent"] = AgentRole.GUARDRAIL_AUDITOR
        state["reasoning_chain"].append(
            f"[GuardrailAuditor] 安全审核: {'通过' if safety_result.is_safe else '拦截! ' + str(violations)}"
        )
        
        state["step"] = state.get("step", 0) + 1
        return state


# =============================================================================
# 多Agent编排器
# =============================================================================

class HPUMultiAgent:
    """
    HPU多智能体系统
    
    使用LangGraph风格的状态机编排多个专业Agent:
    StateEvaluator -> ExerciseCoach -> NutritionPlanner -> GuardrailAuditor
    
    支持:
    - 条件分支 (根据状态决定下一个Agent)
    - 循环回溯 (发现问题返回修改)
    - 工具调用 (Function Calling)
    - 思考链展示 (Chain of Thought)
    """
    
    def __init__(self):
        self.agents = {
            AgentRole.STATE_EVALUATOR: StateEvaluator(),
            AgentRole.EXERCISE_COACH: ExerciseCoach(),
            AgentRole.NUTRITION_PLANNER: NutritionPlanner(),
            AgentRole.GUARDRAIL_AUDITOR: GuardrailAuditor(),
        }
        
        # 工作流定义 (边)
        self.workflow_edges = {
            AgentRole.STATE_EVALUATOR: AgentRole.EXERCISE_COACH,
            AgentRole.EXERCISE_COACH: AgentRole.NUTRITION_PLANNER,
            AgentRole.NUTRITION_PLANNER: AgentRole.GUARDRAIL_AUDITOR,
            AgentRole.GUARDRAIL_AUDITOR: None,  # 结束
        }
    
    def run(self, initial_state: AgentState) -> AgentState:
        """
        运行多Agent工作流
        
        Args:
            initial_state: 初始状态
            
        Returns:
            最终状态
        """
        state = initial_state.copy()
        state["step"] = 0
        state["max_steps"] = 10
        state["reasoning_chain"] = []
        state["decision_history"] = []
        state["status"] = "running"
        
        current_agent_role = AgentRole.STATE_EVALUATOR
        
        while state["step"] < state["max_steps"]:
            if current_agent_role not in self.agents:
                break
            
            agent = self.agents[current_agent_role]
            state = agent.process(state)
            
            # 检查错误
            if state.get("error"):
                state["status"] = "error"
                break
            
            # 移动到下一个Agent
            next_role = self.workflow_edges.get(current_agent_role)
            
            # 条件分支: 如果Guardrail拦截，回退到NutritionPlanner
            if current_agent_role == AgentRole.GUARDRAIL_AUDITOR:
                if state.get("guardrail_active"):
                    state["reasoning_chain"].append("[回溯] 安全拦截，需要重新生成建议")
                    next_role = AgentRole.NUTRITION_PLANNER
                    state["guardrail_active"] = False
                else:
                    next_role = None  # 完成
            
            if next_role is None:
                break
            
            current_agent_role = next_role
        
        state["status"] = "completed" if state["status"] == "running" else state["status"]
        return state
    
    def get_workflow_visualization(self) -> Dict:
        """获取工作流可视化数据"""
        return {
            "nodes": [
                {"id": "state_evaluator", "label": "StateEvaluator", "description": "状态评估器", "icon": "📊"},
                {"id": "exercise_coach", "label": "ExerciseCoach", "description": "训练教练", "icon": "🏋️"},
                {"id": "nutrition_planner", "label": "NutritionPlanner", "description": "营养规划师", "icon": "🍽️"},
                {"id": "guardrail_auditor", "label": "GuardrailAuditor", "description": "安全审计员", "icon": "🛡️"},
            ],
            "edges": [
                {"from": "state_evaluator", "to": "exercise_coach", "label": "数据就绪"},
                {"from": "exercise_coach", "to": "nutrition_planner", "label": "训练计划完成"},
                {"from": "nutrition_planner", "to": "guardrail_auditor", "label": "建议生成"},
                {"from": "guardrail_auditor", "to": "nutrition_planner", "label": "回溯(拦截)"},
            ],
            "current_active": "state_evaluator"
        }
