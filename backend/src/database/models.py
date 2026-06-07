"""
HPU 数据库模型
统一使用 PostgreSQL
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer)
    gender = Column(String(20))  # male, female
    height_cm = Column(Float)
    weight_kg = Column(Float)
    fitness_level = Column(String(50))  # beginner, intermediate, advanced
    goal = Column(String(50))  # lose_weight, maintain, gain_muscle
    activity_level = Column(String(50))
    
    # 关系
    watch_data = relationship("WatchData", back_populates="user", cascade="all, delete-orphan")
    exercise_records = relationship("ExerciseRecord", back_populates="user", cascade="all, delete-orphan")
    nutrition_logs = relationship("NutritionLog", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("AIConversation", back_populates="user", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<User {self.name}>"


class WatchData(Base):
    """手表数据表"""
    __tablename__ = 'watch_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 日期
    date = Column(Date, nullable=False)
    
    # 运动数据
    steps = Column(Integer, default=0)
    exercise_minutes = Column(Integer, default=0)
    calories_burned = Column(Integer, default=0)
    heart_rate_avg = Column(Integer)
    heart_rate_rest = Column(Integer)
    heart_rate_max = Column(Integer)
    
    # HRV数据 (存储为JSON)
    hrv_data = Column(JSON)  # {"sdnn": 45, "rmssd": 38, "lf_hf_ratio": 1.2}
    
    # 睡眠数据
    sleep_data = Column(JSON)  # {"total_hours": 7.5, "deep_sleep_percent": 22, ...}
    
    # 其他指标
    stress_level = Column(Integer)
    blood_oxygen = Column(Integer)
    temperature = Column(Float)
    
    # 原始文件路径
    raw_file_path = Column(String(500))
    
    # 关系
    user = relationship("User", back_populates="watch_data")
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<WatchData user={self.user_id} date={self.date}>"


class ExerciseRecord(Base):
    """运动记录表"""
    __tablename__ = 'exercise_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    date = Column(Date, nullable=False)
    exercise_type = Column(String(100))  # 深蹲, 硬拉, etc.
    
    # 视频分析
    video_path = Column(String(500))
    key_frame_path = Column(String(500))  # 最低点关键帧
    skeleton_image_path = Column(String(500))  # 骨骼标注图
    
    # 分析结果
    analysis_result = Column(JSON)  # {"trunk_angle": 35, "knee_angle": 92, ...}
    form_quality = Column(String(50))  # excellent, good, fair, poor
    warnings = Column(JSON)  # ["核心塌腰警告"]
    
    # 关系
    user = relationship("User", back_populates="exercise_records")
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<ExerciseRecord user={self.user_id} type={self.exercise_type}>"


class NutritionLog(Base):
    """饮食记录表"""
    __tablename__ = 'nutrition_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    date = Column(Date, nullable=False)
    meal_type = Column(String(50))  # breakfast, lunch, dinner, snack
    
    # 图片
    image_path = Column(String(500))
    
    # 识别结果
    recognized_foods = Column(JSON)  # [{"name": "鸡胸肉", "grams": 150, "confidence": 0.95}, ...]
    
    # 营养分析结果
    nutrition_result = Column(JSON)  # {"calories": 780, "protein": 68, "carbs": 95, "fat": 12}
    balance_score = Column(Float)
    
    # 关系
    user = relationship("User", back_populates="nutrition_logs")
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<NutritionLog user={self.user_id} date={self.date}>"


class AIConversation(Base):
    """AI对话记录表"""
    __tablename__ = 'ai_conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(String(100))
    
    # 对话内容
    messages = Column(JSON)  # [{"role": "user", "content": "..."}, ...]
    
    # Agent决策链
    agent_decisions = Column(JSON)  # [{"agent": "StateEvaluator", "tools": [...], ...}]
    
    # 安全检查
    safety_logs = Column(JSON)  # [{"input": "...", "result": "blocked", ...}]
    
    # 输出
    recommendations = Column(JSON)
    training_plan = Column(JSON)
    meal_plan = Column(JSON)
    speech_report = Column(Text)
    
    # 关系
    user = relationship("User", back_populates="conversations")
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<AIConversation user={self.user_id} session={self.session_id}>"


class PromptTemplate(Base):
    """提示词模板表 - 用于AI调教"""
    __tablename__ = 'prompt_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    
    # 模板内容
    template = Column(Text, nullable=False)  # 提示词模板
    
    # 变量定义
    variables = Column(JSON)  # ["user_profile", "health_data", "goals"]
    
    # 版本控制
    version = Column(Integer, default=1)
    is_active = Column(Integer, default=1)
    
    # 使用统计
    use_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)  # 用户反馈成功的次数
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<PromptTemplate {self.name} v{self.version}>"


class SafetyLog(Base):
    """安全日志表"""
    __tablename__ = 'safety_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    
    # 检查内容
    input_text = Column(Text)
    category = Column(String(50))  # injection, medical, privacy
    level = Column(String(20))  # safe, low, medium, high, blocked
    
    # 结果
    violations = Column(JSON)
    warnings = Column(JSON)
    blocked = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<SafetyLog category={self.category} level={self.level}>"


# =============================================================================
# 数据库连接配置 (统一使用PostgreSQL)
# =============================================================================

def get_database_url():
    """
    获取PostgreSQL数据库URL
    
    优先级:
    1. DATABASE_URL 环境变量
    2. PG_* 环境变量组合
    3. 默认本地PostgreSQL
    """
    # 方式1: 直接指定完整URL
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')
    
    # 方式2: 分别指定
    host = os.getenv('PG_HOST', 'localhost')
    port = os.getenv('PG_PORT', '5432')
    database = os.getenv('PG_DATABASE', 'hpu_db')
    user = os.getenv('PG_USER', 'postgres')
    password = os.getenv('PG_PASSWORD', 'winson')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def init_database():
    """初始化数据库连接"""
    db_url = get_database_url()
    engine = create_engine(
        db_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )
    return engine


def get_session():
    """获取数据库会话"""
    engine = init_database()
    Session = sessionmaker(bind=engine)
    return Session()


def create_tables():
    """创建所有表"""
    engine = init_database()
    Base.metadata.create_all(engine)
    return engine


# =============================================================================
# 初始化默认提示词模板
# =============================================================================

DEFAULT_PROMPTS = {
    "system_prompt": """你是HPU健康智能体，专注于健身、饮食和睡眠管理。

你的职责：
1. 分析用户健康数据（来自手表、运动、饮食）
2. 生成个性化训练和饮食建议
3. 识别并拒绝不安全的医疗建议请求

重要约束：
- 不提供医疗诊断
- 不推荐药物或补充剂
- 所有建议仅供参考""",

    "state_evaluator_prompt": """分析以下手表数据，评估用户身体状态：

数据：{watch_data}

请计算并返回：
1. BMI指数
2. 基础代谢率(BMR)
3. 每日总消耗(TDEE)
4. 身体年龄估算
5. 恢复度评分

格式要求：JSON""",

    "exercise_analysis_prompt": """分析以下运动数据，评估动作质量：

关节角度：{angles}
动作类型：{exercise_type}

请判断：
1. 动作质量等级(excellent/good/fair/poor)
2. 是否存在警告（如塌腰）
3. 修正建议

格式要求：JSON""",

    "nutrition_analysis_prompt": """识别以下食物并计算营养：

识别的食物：{detected_foods}
分量：{portions}

请从USDA数据库查询并返回：
- 每种食物的热量和宏量营养素
- 总热量和营养素
- 饮食平衡度评分

格式要求：JSON"""
}


def seed_prompt_templates(session):
    """初始化提示词模板"""
    for name, template in DEFAULT_PROMPTS.items():
        existing = session.query(PromptTemplate).filter_by(name=name).first()
        if not existing:
            pt = PromptTemplate(
                name=name,
                description=f"默认{name}模板",
                template=template,
                variables=["user_profile", "health_data"],
                version=1,
                is_active=1
            )
            session.add(pt)
    session.commit()
