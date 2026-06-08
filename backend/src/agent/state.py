"""
Agent状态定义
定义LangGraph工作流中的状态结构
"""

from typing import TypedDict, List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentRole(str, Enum):
    """Agent角色枚举"""
    STATE_EVALUATOR = "state_evaluator"      # 状态评估器
    EXERCISE_COACH = "exercise_coach"        # 训练教练
    NUTRITION_PLANNER = "nutrition_planner"  # 营养规划师
    GUARDRAIL_AUDITOR = "guardrail_auditor"  # 安全审计员
    ORCHESTRATOR = "orchestrator"            # 编排协调员


@dataclass
class HealthMetrics:
    """健康指标"""
    # 运动数据
    steps: int = 0
    exercise_minutes: int = 0
    calories_burned: int = 0
    heart_rate_avg: int = 70
    
    # 饮食数据
    calories_intake: int = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    
    # 睡眠数据
    sleep_hours: float = 0
    deep_sleep_percent: float = 0
    sleep_quality: int = 7
    
    # 计算指标
    bmi: float = 0
    bmr: int = 0
    tdee: int = 0
    body_age: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "steps": self.steps,
            "exercise_minutes": self.exercise_minutes,
            "calories_burned": self.calories_burned,
            "heart_rate_avg": self.heart_rate_avg,
            "calories_intake": self.calories_intake,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "sleep_hours": self.sleep_hours,
            "deep_sleep_percent": self.deep_sleep_percent,
            "sleep_quality": self.sleep_quality,
            "bmi": self.bmi,
            "bmr": self.bmr,
            "tdee": self.tdee,
            "body_age": self.body_age,
        }


@dataclass
class ExerciseAnalysis:
    """运动分析结果"""
    video_path: Optional[str] = None
    key_frame_path: Optional[str] = None
    skeleton_image_path: Optional[str] = None
    
    # 关节角度
    trunk_angle: float = 0      # 躯干角度
    knee_angle: float = 0       # 膝关节角度
    hip_angle: float = 0        # 髋关节角度
    
    # 评估结果
    form_quality: str = "unknown"  # excellent, good, fair, poor
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    # 修正动作
    corrective_exercises: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "form_quality": self.form_quality,
            "trunk_angle": self.trunk_angle,
            "knee_angle": self.knee_angle,
            "hip_angle": self.hip_angle,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "corrective_exercises": self.corrective_exercises,
        }


@dataclass
class NutritionAnalysis:
    """营养分析结果"""
    image_path: Optional[str] = None
    
    # 识别的食物
    detected_foods: List[Dict] = field(default_factory=list)
    
    # 营养估算
    estimated_calories: int = 0
    estimated_protein: float = 0
    estimated_carbs: float = 0
    estimated_fat: float = 0
    
    # USDA数据来源
    usda_data: Dict = field(default_factory=dict)
    
    # 评估
    balance_score: float = 0  # 0-100
    
    def to_dict(self) -> Dict:
        return {
            "detected_foods": self.detected_foods,
            "estimated_calories": self.estimated_calories,
            "estimated_protein": self.estimated_protein,
            "estimated_carbs": self.estimated_carbs,
            "estimated_fat": self.estimated_fat,
            "usda_data": self.usda_data,
            "balance_score": self.balance_score,
        }


@dataclass 
class SafetyResult:
    """安全检查结果"""
    is_safe: bool = True
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    block_category: str = "none"  # none, injection, medical, privacy, inappropriate
    
    def to_dict(self) -> Dict:
        return {
            "is_safe": self.is_safe,
            "violations": self.violations,
            "warnings": self.warnings,
            "block_category": self.block_category,
        }


@dataclass
class AgentDecision:
    """Agent决策记录"""
    agent_name: str
    agent_role: AgentRole
    timestamp: datetime
    input_data: Dict
    output_data: Dict
    reasoning: str
    tools_called: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role.value,
            "timestamp": self.timestamp.isoformat(),
            "input_data": self.input_data,
            "output_data": self.output_data,
            "reasoning": self.reasoning,
            "tools_called": self.tools_called,
        }


class AgentState(TypedDict):
    """
    LangGraph工作流状态定义
    
    这是整个多Agent系统的核心数据结构，在Agent间流转
    """
    # 用户输入
    user_id: str
    session_id: str
    timestamp: str
    
    # 原始数据
    watch_data: Optional[Dict]           # 手表数据
    exercise_video: Optional[str]        # 运动视频路径
    food_image: Optional[str]            # 食物图片路径
    
    # 分析结果
    health_metrics: Optional[HealthMetrics]
    exercise_analysis: Optional[ExerciseAnalysis]
    nutrition_analysis: Optional[NutritionAnalysis]
    
    # Agent决策链
    current_agent: Optional[AgentRole]
    decision_history: List[Dict]          # AgentDecision列表
    reasoning_chain: List[str]           # 思考链
    
    # 安全检查
    safety_result: Optional[SafetyResult]
    guardrail_active: bool
    
    # 最终输出
    recommendations: List[Dict]           # 最终建议
    training_plan: Optional[Dict]
    meal_plan: Optional[Dict]
    speech_report: Optional[str]
    
    # 工作流控制
    step: int                             # 当前步骤
    max_steps: int                        # 最大步骤数
    error: Optional[str]                   # 错误信息
    status: str                           # running, completed, error, blocked


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    arguments: Dict
    result: Any
    success: bool
    execution_time_ms: float
    api_source: str  # usda, wger, internal, etc.
