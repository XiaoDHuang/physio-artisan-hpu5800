"""
HPU 健身智能体 - 核心Agent实现
基于函数调用的自主智能体系统
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from ..prompts import SYSTEM_PROMPT, contains_injection_attempt
from ..tools import (
    NutritionDB, TrainingTemplates, 
    BodyMetricsCalculator, SleepAnalyzer
)
from ..multimodal import ChartGenerator, SpeechSynthesizer
from ..safety import SafetyGuardrails


@dataclass
class UserProfile:
    """用户基本信息"""
    name: str
    age: int
    gender: str  # "male" or "female"
    height_cm: float
    weight_kg: float
    fitness_level: str  # "beginner", "intermediate", "advanced"
    goal: str  # "lose_weight", "maintain", "gain_muscle"
    activity_level: str  # "sedentary", "light", "moderate", "active", "very_active"


@dataclass
class HealthData:
    """健康数据"""
    date: str
    steps: int = 0
    exercise_minutes: int = 0
    calories_burned: int = 0
    heart_rate_avg: int = 0
    calories_intake: int = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    sleep_hours: float = 0
    deep_sleep_percent: float = 0
    sleep_quality: int = 0  # 1-10


@dataclass
class AgentResponse:
    """Agent响应"""
    success: bool
    message: str
    analysis: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    charts: Optional[List[str]] = None
    speech_report: Optional[str] = None
    safety_warnings: Optional[List[str]] = None


class HPUAgent:
    """
    健康私人智能体 (Health Personal Unit Agent)
    
    核心功能：
    1. 接收用户健康数据
    2. 调用工具函数进行分析
    3. 生成饮食和训练调整建议
    4. 输出多模态报告（图表+语音）
    """
    
    def __init__(self, user_profile: UserProfile):
        self.user_profile = user_profile
        self.tools = self._initialize_tools()
        self.safety = SafetyGuardrails()
        self.chart_gen = ChartGenerator()
        self.speech = SpeechSynthesizer()
        self.conversation_history: List[Dict] = []
        
    def _initialize_tools(self) -> Dict:
        """初始化所有工具"""
        return {
            "nutrition_db": NutritionDB(),
            "training": TrainingTemplates(),
            "calculator": BodyMetricsCalculator(user_profile),
            "sleep": SleepAnalyzer(),
        }
    
    def _register_function_schemas(self) -> List[Dict]:
        """
        定义Agent可调用的函数模式
        这是在实际LLM API中使用的function calling定义
        """
        return [
            {
                "name": "calculate_bmi",
                "description": "计算身体质量指数BMI",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "weight_kg": {"type": "number", "description": "体重(kg)"},
                        "height_cm": {"type": "number", "description": "身高(cm)"}
                    },
                    "required": ["weight_kg", "height_cm"]
                }
            },
            {
                "name": "calculate_bmr",
                "description": "计算基础代谢率",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "weight_kg": {"type": "number"},
                        "height_cm": {"type": "number"},
                        "age": {"type": "integer"},
                        "gender": {"type": "string", "enum": ["male", "female"]}
                    },
                    "required": ["weight_kg", "height_cm", "age", "gender"]
                }
            },
            {
                "name": "calculate_tdee",
                "description": "计算每日总消耗能量",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bmr": {"type": "number"},
                        "activity_level": {"type": "string", "enum": ["sedentary", "light", "moderate", "active", "very_active"]}
                    },
                    "required": ["bmr", "activity_level"]
                }
            },
            {
                "name": "search_nutrition",
                "description": "搜索食物营养信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "food_name": {"type": "string", "description": "食物名称"}
                    },
                    "required": ["food_name"]
                }
            },
            {
                "name": "get_meal_plan",
                "description": "获取个性化饮食计划",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_calories": {"type": "number"},
                        "macro_ratio": {"type": "string", "description": "宏量营养素比例，如'40/30/30'代表碳/蛋/脂"}
                    },
                    "required": ["target_calories"]
                }
            },
            {
                "name": "get_training_template",
                "description": "获取训练模板",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fitness_level": {"type": "string"},
                        "goal": {"type": "string"}
                    },
                    "required": ["fitness_level", "goal"]
                }
            },
            {
                "name": "analyze_sleep",
                "description": "分析睡眠质量",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sleep_hours": {"type": "number"},
                        "deep_sleep_percent": {"type": "number"},
                        "quality_score": {"type": "integer"}
                    },
                    "required": ["sleep_hours", "deep_sleep_percent", "quality_score"]
                }
            },
            {
                "name": "generate_body_age",
                "description": "计算身体年龄",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resting_heart_rate": {"type": "integer"},
                        "bmi": {"type": "number"},
                        "exercise_frequency": {"type": "integer", "description": "每周运动次数"},
                        "sleep_quality": {"type": "number", "description": "睡眠质量评分1-10"}
                    },
                    "required": ["resting_heart_rate", "bmi", "exercise_frequency", "sleep_quality"]
                }
            }
        ]
    
    def _execute_function(self, function_name: str, parameters: Dict) -> Any:
        """执行函数调用"""
        function_map = {
            "calculate_bmi": self.tools["calculator"].calculate_bmi,
            "calculate_bmr": self.tools["calculator"].calculate_bmr,
            "calculate_tdee": self.tools["calculator"].calculate_tdee,
            "search_nutrition": self.tools["nutrition_db"].search,
            "get_meal_plan": self.tools["nutrition_db"].get_meal_plan,
            "get_training_template": self.tools["training"].get_template,
            "analyze_sleep": self.tools["sleep"].analyze,
            "generate_body_age": self.tools["calculator"].calculate_body_age,
        }
        
        func = function_map.get(function_name)
        if func:
            return func(**parameters)
        raise ValueError(f"Unknown function: {function_name}")
    
    def _validate_input(self, user_input: str) -> bool:
        """验证输入安全性"""
        if contains_injection_attempt(user_input):
            return False
        return True
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """基于分析结果生成建议"""
        recommendations = []
        profile = self.user_profile
        
        # 运动建议
        if analysis.get("exercise_deficit", 0) > 200:
            recommendations.append(
                f"今日运动量偏少，建议增加{analysis['exercise_deficit']}kcal的运动消耗，"
                f"可以尝试快走{int(analysis['exercise_deficit']/5)}分钟"
            )
        
        # 饮食建议
        if analysis.get("calorie_balance") == "surplus":
            recommendations.append(
                "今日摄入热量偏高，建议增加运动量或调整晚餐结构，"
                "增加蔬菜和蛋白质的比例"
            )
        elif analysis.get("calorie_balance") == "deficit":
            recommendations.append(
                "摄入热量适中，注意保持均衡营养"
            )
        
        # 睡眠建议
        if analysis.get("sleep_quality_score", 10) < 6:
            recommendations.append(
                "睡眠质量有待提升，建议睡前减少电子设备使用，"
                "保持规律作息时间"
            )
        
        # 训练计划调整
        if analysis.get("weekly_progress"):
            recommendations.append(
                f"本周已完成{analysis['weekly_progress']}次训练，"
                "建议明天安排力量训练"
            )
        
        return recommendations
    
    def _generate_text_report(self, health_data: HealthData, analysis: Dict) -> str:
        """生成文本分析报告"""
        date_str = health_data.date or datetime.now().strftime("%Y-%m-%d")
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║              📊 {date_str} 健康分析报告                      ║
╚══════════════════════════════════════════════════════════════╝

🏃 【运动数据】
   • 步数: {health_data.steps:,} 步
   • 运动时长: {health_data.exercise_minutes} 分钟
   • 消耗热量: {health_data.calories_burned} kcal

🍽️ 【饮食数据】
   • 摄入热量: {health_data.calories_intake} kcal
   • 蛋白质: {health_data.protein_g}g
   • 碳水化合物: {health_data.carbs_g}g
   • 脂肪: {health_data.fat_g}g

😴 【睡眠数据】
   • 睡眠时长: {health_data.sleep_hours} 小时
   • 深睡比例: {health_data.deep_sleep_percent}%
   • 睡眠质量: {health_data.sleep_quality}/10

📈 【健康指标】
   • BMI: {analysis.get('bmi', 'N/A')}
   • 基础代谢率: {analysis.get('bmr', 'N/A')} kcal/天
   • 身体年龄: {analysis.get('body_age', 'N/A')} 岁

💡 【智能建议】
"""
        for i, rec in enumerate(analysis.get('recommendations', []), 1):
            report += f"   {i}. {rec}\n"
        
        report += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  免责声明：本报告仅供参考，不构成医疗建议。
    如有健康问题，请咨询专业医生。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return report
    
    def process_health_data(self, health_data: HealthData) -> AgentResponse:
        """
        处理健康数据的主入口
        这是Agent的核心工作流程
        """
        # 1. 安全检查
        safety_warnings = self.safety.check_input(str(health_data))
        if safety_warnings:
            return AgentResponse(
                success=False,
                message="输入包含不安全内容",
                safety_warnings=safety_warnings
            )
        
        try:
            # 2. 调用工具进行计算和分析
            calc = self.tools["calculator"]
            
            bmi = calc.calculate_bmi(
                health_data.weight_kg if hasattr(health_data, 'weight_kg') else self.user_profile.weight_kg,
                health_data.height_cm if hasattr(health_data, 'height_cm') else self.user_profile.height_cm
            )
            
            bmr = calc.calculate_bmr(
                self.user_profile.weight_kg,
                self.user_profile.height_cm,
                self.user_profile.age,
                self.user_profile.gender
            )
            
            tdee = calc.calculate_tdee(bmr, self.user_profile.activity_level)
            
            body_age = calc.calculate_body_age(
                resting_heart_rate=health_data.heart_rate_avg or 70,
                bmi=bmi,
                exercise_frequency=4,  # 假设每周4次
                sleep_quality=health_data.sleep_quality or 7
            )
            
            # 睡眠分析
            sleep_analysis = self.tools["sleep"].analyze(
                health_data.sleep_hours,
                health_data.deep_sleep_percent,
                health_data.sleep_quality
            )
            
            # 计算热量平衡
            calorie_balance = health_data.calories_intake - health_data.calories_burned
            if calorie_balance > 200:
                balance_status = "surplus"
            elif calorie_balance < -200:
                balance_status = "deficit"
            else:
                balance_status = "balanced"
            
            # 3. 组装分析结果
            analysis = {
                "bmi": round(bmi, 1),
                "bmr": int(bmr),
                "tdee": int(tdee),
                "body_age": body_age,
                "sleep_quality_score": sleep_analysis.get("quality_score", 7),
                "calorie_balance": balance_status,
                "exercise_deficit": max(0, tdee - health_data.calories_burned),
                "recommendations": self._generate_recommendations({
                    "exercise_deficit": max(0, tdee - health_data.calories_burned),
                    "calorie_balance": balance_status,
                    "sleep_quality_score": sleep_analysis.get("quality_score", 7),
                    "weekly_progress": 3
                })
            }
            
            # 4. 生成多模态输出
            chart_paths = self.chart_gen.generate_report_chart(health_data, analysis)
            speech_text = self.speech.generate_report(health_data, analysis)
            
            # 5. 返回响应
            return AgentResponse(
                success=True,
                message="分析完成",
                analysis=analysis,
                recommendations=analysis["recommendations"],
                charts=chart_paths,
                speech_report=speech_text
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"分析出错: {str(e)}",
                safety_warnings=["系统错误，请重试"]
            )
    
    def generate_adjusted_plan(self, health_data: HealthData) -> Dict:
        """
        生成调整后的饮食和训练计划
        展示Agent的自主决策能力
        """
        # 获取当前分析
        response = self.process_health_data(health_data)
        
        if not response.success:
            return {"error": response.message}
        
        analysis = response.analysis
        tdee = analysis.get("tdee", 2000)
        
        # 根据目标调整热量
        goal = self.user_profile.goal
        if goal == "lose_weight":
            target_calories = int(tdee * 0.8)  # 80% TDEE
        elif goal == "gain_muscle":
            target_calories = int(tdee * 1.1)  # 110% TDEE
        else:
            target_calories = tdee
        
        # 获取饮食计划
        meal_plan = self.tools["nutrition_db"].get_meal_plan(
            target_calories=target_calories,
            macro_ratio="40/30/30"  # 默认比例
        )
        
        # 获取训练计划
        training_plan = self.tools["training"].generate_plan(
            user_profile=self.user_profile,
            days_per_week=4
        )
        
        return {
            "date": health_data.date,
            "adjusted_calories": target_calories,
            "meal_plan": meal_plan,
            "training_plan": training_plan,
            "analysis": analysis,
            "charts": response.charts,
            "speech_report": response.speech_report
        }
    
    def chat(self, user_message: str) -> AgentResponse:
        """
        聊天接口
        处理用户自然语言输入
        """
        # 安全检查
        if not self._validate_input(user_message):
            return AgentResponse(
                success=False,
                message="输入包含无效内容，请重新输入",
                safety_warnings=["检测到潜在的不当输入"]
            )
        
        # 记录对话历史
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # 意图识别（简化版）
        if "分析" in user_message or "报告" in user_message:
            return AgentResponse(
                success=True,
                message="请提供今日的健康数据，我将为您生成分析报告",
                recommendations=["需要运动数据（步数、运动时长、消耗卡路里）",
                              "需要饮食数据（摄入热量、蛋白质、碳水、脂肪）",
                              "需要睡眠数据（睡眠时长、深睡比例、质量评分）"]
            )
        elif "计划" in user_message or "建议" in user_message:
            return AgentResponse(
                success=True,
                message="我可以为您生成个性化的训练和饮食计划",
                recommendations=["请告诉我您的健身目标（减脂/增肌/维持）",
                              "您每周可以训练几天？"]
            )
        elif "身体年龄" in user_message:
            bmi = self.tools["calculator"].calculate_bmi(
                self.user_profile.weight_kg,
                self.user_profile.height_cm
            )
            body_age = self.tools["calculator"].calculate_body_age(
                resting_heart_rate=70,
                bmi=bmi,
                exercise_frequency=4,
                sleep_quality=7
            )
            return AgentResponse(
                success=True,
                message=f"根据您的基础数据估算，身体年龄约为 {body_age} 岁",
                analysis={"body_age": body_age}
            )
        else:
            return AgentResponse(
                success=True,
                message="我是HPU健康智能体，可以帮您分析健康数据、生成饮食训练计划。请问有什么可以帮您？",
                recommendations=["输入'分析'查看健康报告格式",
                              "输入'计划'获取个性化建议"]
            )
    
    def get_function_schemas(self) -> List[Dict]:
        """获取函数模式定义，用于LLM的function calling"""
        return self._register_function_schemas()
