-- ================================================
-- HPU 健康智能体 - 数据库初始化SQL
-- 执行方式: psql -U postgres -d postgres -f init_hpu.sql
-- 或直接在Navicat/pgAdmin中执行
-- ================================================

-- 1. 创建数据库
CREATE DATABASE hpu_db;

-- 2. 连接数据库
-- \c hpu_db;

-- ================================================
-- 3. 创建表结构
-- ================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INTEGER,
    gender VARCHAR(20),
    height_cm FLOAT,
    weight_kg FLOAT,
    fitness_level VARCHAR(50),
    goal VARCHAR(50),
    activity_level VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 手表数据表
CREATE TABLE IF NOT EXISTS watch_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    steps INTEGER DEFAULT 0,
    exercise_minutes INTEGER DEFAULT 0,
    calories_burned INTEGER DEFAULT 0,
    heart_rate_avg INTEGER,
    heart_rate_rest INTEGER,
    heart_rate_max INTEGER,
    hrv_data JSONB,
    sleep_data JSONB,
    stress_level INTEGER,
    blood_oxygen INTEGER,
    temperature FLOAT,
    raw_file_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 运动记录表
CREATE TABLE IF NOT EXISTS exercise_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    exercise_type VARCHAR(100),
    video_path VARCHAR(500),
    key_frame_path VARCHAR(500),
    skeleton_image_path VARCHAR(500),
    analysis_result JSONB,
    form_quality VARCHAR(50),
    warnings JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 饮食记录表
CREATE TABLE IF NOT EXISTS nutrition_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    meal_type VARCHAR(50),
    image_path VARCHAR(500),
    recognized_foods JSONB,
    nutrition_result JSONB,
    balance_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI对话记录表
CREATE TABLE IF NOT EXISTS ai_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(100),
    messages JSONB,
    agent_decisions JSONB,
    safety_logs JSONB,
    recommendations JSONB,
    training_plan JSONB,
    meal_plan JSONB,
    speech_report TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 提示词模板表
CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    template TEXT NOT NULL,
    variables JSONB,
    version INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    use_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 安全日志表
CREATE TABLE IF NOT EXISTS safety_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    input_text TEXT,
    category VARCHAR(50),
    level VARCHAR(20),
    violations JSONB,
    warnings JSONB,
    blocked INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================
-- 4. 创建索引
-- ================================================

CREATE INDEX IF NOT EXISTS idx_watch_data_user_id ON watch_data(user_id);
CREATE INDEX IF NOT EXISTS idx_watch_data_date ON watch_data(date);
CREATE INDEX IF NOT EXISTS idx_exercise_records_user_id ON exercise_records(user_id);
CREATE INDEX IF NOT EXISTS idx_nutrition_logs_user_id ON nutrition_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_nutrition_logs_date ON nutrition_logs(date);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_safety_logs_user_id ON safety_logs(user_id);

-- ================================================
-- 5. 插入默认提示词模板
-- ================================================

INSERT INTO prompt_templates (name, description, template, variables, is_active)
VALUES 
('system_prompt', '系统提示词模板', 
'你是HPU健康智能体，专注于健身、饮食和睡眠管理。

你的职责：
1. 分析用户健康数据（来自手表、运动、饮食）
2. 生成个性化训练和饮食建议
3. 识别并拒绝不安全的医疗建议请求

重要约束：
- 不提供医疗诊断
- 不推荐药物或补充剂
- 所有建议仅供参考', 
'["user_profile", "health_data"]', 1),

('state_evaluator_prompt', '状态评估提示词', 
'分析以下手表数据，评估用户身体状态：

数据：{watch_data}

请计算并返回：
1. BMI指数
2. 基础代谢率(BMR)
3. 每日总消耗(TDEE)
4. 身体年龄估算
5. 恢复度评分

格式要求：JSON', 
'["watch_data"]', 1),

('exercise_analysis_prompt', '运动分析提示词', 
'分析以下运动数据，评估动作质量：

关节角度：{angles}
动作类型：{exercise_type}

请判断：
1. 动作质量等级(excellent/good/fair/poor)
2. 是否存在警告（如塌腰）
3. 修正建议

格式要求：JSON', 
'["angles", "exercise_type"]', 1),

('nutrition_analysis_prompt', '营养分析提示词', 
'识别以下食物并计算营养：

识别的食物：{detected_foods}
分量：{portions}

请从USDA数据库查询并返回：
- 每种食物的热量和宏量营养素
- 总热量和营养素
- 饮食平衡度评分

格式要求：JSON', 
'["detected_foods", "portions"]', 1)

ON CONFLICT (name) DO NOTHING;

-- ================================================
-- 6. 创建测试用户
-- ================================================

INSERT INTO users (name, age, gender, height_cm, weight_kg, fitness_level, goal, activity_level)
VALUES
    ('演示用户', 28, 'male', 175, 72, 'intermediate', 'lose_weight', 'moderate'),
    ('李四', 25, 'female', 162, 55, 'beginner', 'maintain', 'light'),
    ('王五', 35, 'male', 180, 80, 'advanced', 'gain_muscle', 'very_active')
ON CONFLICT DO NOTHING;

-- ================================================
-- 7. 创建测试手表数据
-- ================================================

INSERT INTO watch_data (user_id, date, steps, exercise_minutes, calories_burned, heart_rate_avg, heart_rate_rest, hrv_data, sleep_data)
VALUES 
(1, CURRENT_DATE, 12500, 65, 2850, 72, 58, '{"sdnn": 45, "rmssd": 38, "lf_hf_ratio": 1.2}', '{"total_hours": 7.5, "deep_sleep_percent": 22, "sleep_score": 85}')
ON CONFLICT DO NOTHING;

-- ================================================
-- 完成
-- ================================================

