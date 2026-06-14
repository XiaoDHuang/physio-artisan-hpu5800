-- ================================================
-- 「暴汗艺术家」数据协议 v3.1 —— 协议表完整 SQL
-- 用途：三个 Vue 页面（运动/睡眠/饮食）所需的全部数据表
--       - 可独立 psql 执行（不需要先有表）
--       - 全部 CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS，幂等可重跑
--       - 兼容现有增量脚本（migrate_v3_1.sql）；同时给一份完整版供"全新 DB"用
-- 配套：
--   - docs/数据协议 v3.1.md    （K&V 字段定死版）
--   - backend/schemas/data_protocol.py （Pydantic Schema）
--   - backend/api_v31.py        （5 个 GET 端点 + simulator + sleep/log）
-- 执行：
--   psql -U postgres -d hpu_db -f backend/sql/tables_v31_full.sql
-- ================================================

-- 关闭 NOTICE 噪音，保持输出清洁
SET client_min_messages = WARNING;

-- ================================================
-- 0. 触发器函数（被多个表共用）
-- ================================================
CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

-- ================================================
-- 1. users —— 用户主表（含 v3.1 顶层字段冗余）
-- ================================================
CREATE TABLE IF NOT EXISTS users (
    id                SERIAL PRIMARY KEY,                -- 用户主键
    name              VARCHAR(64),                       -- 姓名
    age               INT,                               -- 实际年龄（岁）
    gender            VARCHAR(20),                       -- 性别：male / female / other
    height_cm         FLOAT,                             -- 身高（cm）
    weight_kg         FLOAT,                             -- 体重（kg），用于 R4 蛋白/kg 计算
    body_fat_pct      FLOAT,                             -- 体脂率（%）
    body_age          FLOAT,                             -- 身体年龄（岁），仿真器算
    muscle_mass_kg    FLOAT,                             -- 肌肉量（kg）
    fitness_level     VARCHAR(50),                       -- 健身水平：beginner / intermediate / advanced
    goal              VARCHAR(50),                       -- 目标：lose_weight / gain_muscle / maintain
    activity_level    VARCHAR(50),                       -- 活动水平：light / moderate / very_active
    -- v3.1 顶层通用字段
    schema_version    VARCHAR(20)  DEFAULT '3.1.0',      -- 协议版本号（固定 3.1.0）
    tz_offset         VARCHAR(10)  DEFAULT '+08:00',     -- 时区偏移
    chronological_age INT,                               -- 实际年龄冗余（v3.1）
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 账户创建时间
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 更新时间
);
-- 老表增量补列
ALTER TABLE users ADD COLUMN IF NOT EXISTS gender             VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS height_cm          FLOAT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS fitness_level      VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS goal               VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS activity_level     VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS schema_version     VARCHAR(20) DEFAULT '3.1.0';
ALTER TABLE users ADD COLUMN IF NOT EXISTS tz_offset          VARCHAR(10) DEFAULT '+08:00';
ALTER TABLE users ADD COLUMN IF NOT EXISTS chronological_age  INT;
UPDATE users SET chronological_age = age
 WHERE chronological_age IS NULL AND age IS NOT NULL;
COMMENT ON TABLE users IS '用户主表（v3.1 顶层字段冗余）';
COMMENT ON COLUMN users.id                IS '用户主键';
COMMENT ON COLUMN users.name              IS '姓名';
COMMENT ON COLUMN users.age               IS '实际年龄（岁）';
COMMENT ON COLUMN users.gender            IS '性别：male / female / other';
COMMENT ON COLUMN users.height_cm         IS '身高（cm）';
COMMENT ON COLUMN users.weight_kg         IS '体重（kg），用于 R4 蛋白/kg 计算';
COMMENT ON COLUMN users.body_fat_pct      IS '体脂率（%）';
COMMENT ON COLUMN users.body_age          IS '身体年龄（岁），仿真器算';
COMMENT ON COLUMN users.muscle_mass_kg    IS '肌肉量（kg）';
COMMENT ON COLUMN users.fitness_level     IS '健身水平：beginner / intermediate / advanced';
COMMENT ON COLUMN users.goal              IS '目标：lose_weight / gain_muscle / maintain';
COMMENT ON COLUMN users.activity_level    IS '活动水平：light / moderate / very_active';
COMMENT ON COLUMN users.schema_version    IS '协议版本号（固定 3.1.0）';
COMMENT ON COLUMN users.tz_offset         IS '时区偏移（默认 +08:00）';
COMMENT ON COLUMN users.chronological_age IS '实际年龄冗余（v3.1）';

-- ================================================
-- 2. watch_data —— 手表采集的身体/睡眠原始数据
--    3 个 Vue 页面的数据源（特别是睡眠页）
--    对应协议：body_state / cardiovascular / sleep_execution
-- ================================================
CREATE TABLE IF NOT EXISTS watch_data (
    id                      SERIAL PRIMARY KEY,
    user_id                 INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date                    DATE NOT NULL,

    -- 老字段（兼容 hpu_db.sql）
    steps                   INTEGER DEFAULT 0,           -- 步数
    exercise_minutes        INTEGER DEFAULT 0,           -- 运动分钟
    calories_burned         INTEGER DEFAULT 0,           -- 总消耗（含基础代谢）
    heart_rate_avg          INTEGER,                     -- 平均心率
    heart_rate_max          INTEGER,                     -- 最大心率
    stress_level            INTEGER,                     -- 压力等级
    blood_oxygen            INTEGER,                     -- 血氧饱和度
    temperature             FLOAT,                       -- 体温
    raw_file_path           VARCHAR(500),                -- 原始数据文件路径

    -- v3.1 body_state 字段冗余
    weight_kg               FLOAT,
    body_fat_pct            FLOAT,
    body_age                FLOAT,
    lean_mass_kg            FLOAT,

    -- v3.1 cardiovascular 字段（HR/HRV）
    heart_rate_rest         INT,
    hrv_data                JSONB,
    hrv_trend_7d            FLOAT,
    hrr                     INT,    -- 新增：心率恢复力（驱动 R1）

    -- v3.1 sleep_execution 字段
    actual_bedtime          VARCHAR(5),
    actual_wake_time        VARCHAR(5),
    total_sleep_min         INT,
    sleep_score             INT,
    deep_sleep_min          INT,
    deep_sleep_pct          FLOAT,
    light_sleep_min         INT,
    rem_sleep_min           INT,
    awake_min               INT,
    sleep_efficiency        FLOAT,
    rr_intervals            JSONB,
    rr_extraction_window    VARCHAR(20),

    -- v3.1.1 扩展：nap
    nap_min                 INT DEFAULT 0,
    nap_score               INT DEFAULT 0,

    -- 旧 JSONB 镜像（兼容历史）
    sleep_data              JSONB,

    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_watch_data_user_id ON watch_data(user_id);
CREATE INDEX IF NOT EXISTS idx_watch_data_date    ON watch_data(date);

-- watch_data 字段增量（兼容已存在的老表）
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS steps                 INTEGER DEFAULT 0;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS exercise_minutes      INTEGER DEFAULT 0;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS calories_burned       INTEGER DEFAULT 0;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS heart_rate_avg        INTEGER;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS heart_rate_max        INTEGER;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS stress_level          INTEGER;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS blood_oxygen          INTEGER;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS temperature           FLOAT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS raw_file_path         VARCHAR(500);
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS weight_kg             FLOAT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS body_fat_pct          FLOAT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS body_age              FLOAT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS lean_mass_kg          FLOAT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS hrv_trend_7d          FLOAT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS hrr                   INT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS actual_bedtime        VARCHAR(5);
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS actual_wake_time      VARCHAR(5);
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS total_sleep_min       INT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS deep_sleep_min        INT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS light_sleep_min       INT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS rem_sleep_min         INT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS awake_min             INT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS sleep_efficiency      FLOAT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS deep_sleep_pct        FLOAT;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS rr_intervals          JSONB;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS rr_extraction_window  VARCHAR(20);
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS nap_min               INT DEFAULT 0;
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS nap_score             INT DEFAULT 0;

COMMENT ON TABLE watch_data IS 'v3.1: 手表采集的身体/睡眠原始数据（睡眠页核心源）';
COMMENT ON COLUMN watch_data.id                   IS '主键';
COMMENT ON COLUMN watch_data.user_id              IS '用户 ID（FK → users.id）';
COMMENT ON COLUMN watch_data.date                 IS '测量日期（YYYY-MM-DD）';
COMMENT ON COLUMN watch_data.steps                IS '步数（兼容 hpu_db.sql 老字段）';
COMMENT ON COLUMN watch_data.exercise_minutes     IS '运动分钟数（兼容老字段）';
COMMENT ON COLUMN watch_data.calories_burned      IS '总消耗 kcal（含基础代谢，兼容老字段）';
COMMENT ON COLUMN watch_data.heart_rate_avg       IS '全天平均心率（bpm，兼容老字段）';
COMMENT ON COLUMN watch_data.heart_rate_max       IS '全天最大心率（bpm，兼容老字段）';
COMMENT ON COLUMN watch_data.heart_rate_rest      IS '晨间静息心率（bpm，v3.1 cardiovascular 字段）';
COMMENT ON COLUMN watch_data.hrv_data             IS 'HRV 完整 JSONB（含 rmssd / sdnn / pnn50）';
COMMENT ON COLUMN watch_data.hrv_trend_7d         IS '7 日 HRV 变化率（%，衍生）';
COMMENT ON COLUMN watch_data.hrr                  IS '心率恢复力（bpm = peak_hr - hr_60s_after，驱动 R1 规则）';
COMMENT ON COLUMN watch_data.stress_level         IS '压力等级（兼容老字段）';
COMMENT ON COLUMN watch_data.blood_oxygen         IS '血氧饱和度（兼容老字段）';
COMMENT ON COLUMN watch_data.temperature          IS '体温（℃）';
COMMENT ON COLUMN watch_data.raw_file_path        IS '原始数据文件路径（兼容老字段）';
COMMENT ON COLUMN watch_data.weight_kg            IS '体重（kg），来自体测秤（v3.1 body_state 字段冗余）';
COMMENT ON COLUMN watch_data.body_fat_pct         IS '体脂率（%）（v3.1 body_state 字段冗余）';
COMMENT ON COLUMN watch_data.body_age             IS '身体年龄（岁，仿真器算）';
COMMENT ON COLUMN watch_data.lean_mass_kg         IS '去脂体重（kg，衍生：weight × (1 - body_fat_pct/100)）';
COMMENT ON COLUMN watch_data.actual_bedtime       IS '实际入睡时间（HH:MM，睡眠页核心）';
COMMENT ON COLUMN watch_data.actual_wake_time     IS '实际起床时间（HH:MM，睡眠页核心）';
COMMENT ON COLUMN watch_data.total_sleep_min      IS '总睡眠时长（分钟，驱动 R3/R5 规则）';
COMMENT ON COLUMN watch_data.sleep_score          IS '综合睡眠评分（0-100，驱动 R3 规则）';
COMMENT ON COLUMN watch_data.deep_sleep_min       IS '深睡时长（分钟，驱动 R4 规则）';
COMMENT ON COLUMN watch_data.deep_sleep_pct       IS '深睡占比（0-1，衍生：deep_sleep_min / total_sleep_min，UI 直接展示）';
COMMENT ON COLUMN watch_data.light_sleep_min      IS '浅睡时长（分钟）';
COMMENT ON COLUMN watch_data.rem_sleep_min        IS 'REM 时长（分钟）';
COMMENT ON COLUMN watch_data.awake_min            IS '清醒时长（分钟）';
COMMENT ON COLUMN watch_data.sleep_efficiency     IS '睡眠效率（0-1，衍生：total_sleep_min / 在床分钟）';
COMMENT ON COLUMN watch_data.rr_intervals         IS '深睡期 10 段相邻 RR 间期（ms，HRV 时序卡）';
COMMENT ON COLUMN watch_data.rr_extraction_window IS 'RR 提取窗口（HH:MM-HH:MM，可追溯）';
COMMENT ON COLUMN watch_data.nap_min              IS '小憩分钟数，0=无小憩（v3.1.1 扩展，睡眠页小憩卡）';
COMMENT ON COLUMN watch_data.nap_score            IS '小憩质量评分（0-100）';
COMMENT ON COLUMN watch_data.sleep_data           IS 'JSONB 冗余镜像：{sleep_score, total_hours, deep_sleep_percent, rem_sleep_percent, stages_timeline}';
COMMENT ON COLUMN watch_data.created_at           IS '入库时间';

-- ================================================
-- 3. exercise_records —— 运动记录（运动页数据源）
--    对应协议：exercise_execution
-- ================================================
CREATE TABLE IF NOT EXISTS exercise_records (
    id                          SERIAL PRIMARY KEY,
    user_id                     INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date                        DATE NOT NULL,

    -- 老字段（兼容 hpu_db.sql）
    exercise_type               VARCHAR(100),                -- 运动类型（兼容老字段）
    video_path                  VARCHAR(500),                -- 视频文件路径
    key_frame_path              VARCHAR(500),                -- 关键帧图路径
    skeleton_image_path         VARCHAR(500),                -- 骨架图路径
    form_quality                VARCHAR(50),                 -- 动作质量：excellent / good / fair / poor
    warnings                    JSONB,                       -- 警告 JSONB

    -- v3.1 exercise_execution 完整字段
    user_choice                 VARCHAR(20),   -- comply | reject
    actual_duration_min         INT,
    actual_rpe                  INT,
    avg_hr                      INT,
    peak_hr                     INT,
    hr_60s_after                INT,
    calories_burned             INT,
    completion_rate             FLOAT,         -- 0-1
    completion_rate_display     INT,           -- 0-100
    hr_series                   JSONB,         -- 60 个 int
    hr_series_timestamps        JSONB,         -- 60 个 int (ms)

    -- 旧字段（兼容）
    analysis_result             JSONB,
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_exercise_records_user_id ON exercise_records(user_id);
CREATE INDEX IF NOT EXISTS idx_exercise_records_date    ON exercise_records(date);

-- 增量补列
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS exercise_type           VARCHAR(100);
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS video_path              VARCHAR(500);
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS key_frame_path          VARCHAR(500);
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS skeleton_image_path     VARCHAR(500);
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS form_quality            VARCHAR(50);
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS warnings                JSONB;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS user_choice             VARCHAR(20);
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS actual_duration_min     INT;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS actual_rpe              INT;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS avg_hr                  INT;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS peak_hr                 INT;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS hr_60s_after            INT;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS calories_burned         INT;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS completion_rate         FLOAT;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS completion_rate_display INT;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS hr_series               JSONB;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS hr_series_timestamps    JSONB;
COMMENT ON TABLE exercise_records IS 'v3.1: 运动记录（运动页核心源）';
COMMENT ON COLUMN exercise_records.id                     IS '主键';
COMMENT ON COLUMN exercise_records.user_id                IS '用户 ID（FK → users.id）';
COMMENT ON COLUMN exercise_records.date                   IS '训练日期（YYYY-MM-DD）';
COMMENT ON COLUMN exercise_records.exercise_type          IS '运动类型（兼容老字段，如"深蹲"/"跑步"）';
COMMENT ON COLUMN exercise_records.video_path             IS '视频文件路径（兼容老字段）';
COMMENT ON COLUMN exercise_records.key_frame_path         IS '关键帧图片路径（兼容老字段）';
COMMENT ON COLUMN exercise_records.skeleton_image_path    IS '骨架图路径（兼容老字段）';
COMMENT ON COLUMN exercise_records.form_quality           IS '动作质量：excellent / good / fair / poor（兼容老字段）';
COMMENT ON COLUMN exercise_records.warnings               IS '警告 JSONB 数组（兼容老字段）';
COMMENT ON COLUMN exercise_records.user_choice            IS '用户当日选择：comply（听话）/ reject（硬练），驱动仿真核心';
COMMENT ON COLUMN exercise_records.actual_duration_min    IS '实际训练时长（分钟）';
COMMENT ON COLUMN exercise_records.actual_rpe             IS '实际 RPE（1-10，驱动 R2/R5 规则）';
COMMENT ON COLUMN exercise_records.avg_hr                 IS '运动平均心率（bpm，运动页"平均心率"卡）';
COMMENT ON COLUMN exercise_records.peak_hr                IS '运动峰值心率（bpm，运动页"最大心率"卡）';
COMMENT ON COLUMN exercise_records.hr_60s_after           IS '运动后 60 秒恢复心率（bpm，用于算 HRR）';
COMMENT ON COLUMN exercise_records.calories_burned        IS '主动消耗热量（kcal，运动页"训练消耗"卡）';
COMMENT ON COLUMN exercise_records.completion_rate        IS '计划完成度（0-1，驱动 R1 规则）';
COMMENT ON COLUMN exercise_records.completion_rate_display IS '完成度 UI 直接展示（0-100，冗余：completion_rate × 100）';
COMMENT ON COLUMN exercise_records.hr_series              IS '运动结束 60 秒内每秒心率（0-300 个 int，bpm，高分辨率曲线）';
COMMENT ON COLUMN exercise_records.hr_series_timestamps   IS '与 hr_series 对齐的时间戳（0-300 个 int，毫秒，t=0 起点）';
COMMENT ON COLUMN exercise_records.analysis_result        IS '旧 JSONB 镜像（兼容历史）';
COMMENT ON COLUMN exercise_records.created_at             IS '入库时间';

-- ================================================
-- 4. nutrition_logs —— 饮食日志（饮食页数据源）
--    对应协议：diet_execution
-- ================================================
CREATE TABLE IF NOT EXISTS nutrition_logs (
    id                      SERIAL PRIMARY KEY,
    user_id                 INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date                    DATE NOT NULL,

    -- 老字段（兼容 hpu_db.sql）
    meal_type               VARCHAR(50),                  -- 餐次（兼容老字段）
    image_path              VARCHAR(500),                 -- 餐食图片路径
    recognized_foods        JSONB,                        -- 识别出的食物 JSONB
    balance_score           FLOAT,                        -- 饮食平衡度评分（0-1）

    -- v3.1 diet_execution 完整字段
    total_calories_actual   INT,
    calories_remaining      INT,             -- 衍生：actual - target
    protein_g               INT,
    carbs_g                 INT,
    fat_g                   INT,
    protein_per_kg          FLOAT,           -- 衍生：protein_g / weight_kg
    adherence_rate          FLOAT,           -- 0-1
    narrative               TEXT,
    meal_breakdown          JSONB,           -- UI 三餐卡

    -- 旧字段（兼容）
    nutrition_result        JSONB,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_nutrition_logs_user_id ON nutrition_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_nutrition_logs_date    ON nutrition_logs(date);

-- 增量补列
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS meal_type              VARCHAR(50);
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS image_path             VARCHAR(500);
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS recognized_foods       JSONB;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS balance_score          FLOAT;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS total_calories_actual  INT;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS calories_remaining     INT;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS protein_g              INT;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS carbs_g                INT;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS fat_g                  INT;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS protein_per_kg         FLOAT;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS adherence_rate         FLOAT;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS narrative              TEXT;
ALTER TABLE nutrition_logs ADD COLUMN IF NOT EXISTS meal_breakdown         JSONB;
COMMENT ON TABLE nutrition_logs IS 'v3.1: 饮食日志（饮食页核心源）';
COMMENT ON COLUMN nutrition_logs.id                    IS '主键';
COMMENT ON COLUMN nutrition_logs.user_id               IS '用户 ID（FK → users.id）';
COMMENT ON COLUMN nutrition_logs.date                  IS '饮食日期（YYYY-MM-DD）';
COMMENT ON COLUMN nutrition_logs.meal_type             IS '餐次：breakfast / lunch / dinner / snack（兼容老字段）';
COMMENT ON COLUMN nutrition_logs.image_path            IS '餐食图片路径（兼容老字段）';
COMMENT ON COLUMN nutrition_logs.recognized_foods      IS '识别出的食物 JSONB 数组（兼容老字段）';
COMMENT ON COLUMN nutrition_logs.balance_score         IS '饮食平衡度评分（0-1，兼容老字段）';
COMMENT ON COLUMN nutrition_logs.total_calories_actual IS '实际总摄入（kcal，饮食页"摄入"卡）';
COMMENT ON COLUMN nutrition_logs.calories_remaining    IS '剩余 vs 目标（kcal，衍生：actual - target，饮食页"剩余"卡）';
COMMENT ON COLUMN nutrition_logs.protein_g             IS '实际蛋白质（g，驱动 R4 规则）';
COMMENT ON COLUMN nutrition_logs.carbs_g               IS '实际碳水（g）';
COMMENT ON COLUMN nutrition_logs.fat_g                 IS '实际脂肪（g）';
COMMENT ON COLUMN nutrition_logs.protein_per_kg        IS '蛋白/kg 体重（g/kg，衍生：protein_g / weight_kg，驱动 R4）';
COMMENT ON COLUMN nutrition_logs.adherence_rate        IS '饮食依从度（0-1，0=完全没吃计划，1=完全按计划）';
COMMENT ON COLUMN nutrition_logs.narrative             IS '实际吃了什么（自由文本 0-500 字）';
COMMENT ON COLUMN nutrition_logs.meal_breakdown        IS '三餐卡 JSONB：[{"meal":"早餐","calories":380,"protein_g":32}, ...]';
COMMENT ON COLUMN nutrition_logs.nutrition_result      IS '旧 JSONB 镜像（兼容历史）';
COMMENT ON COLUMN nutrition_logs.created_at            IS '入库时间';

-- ================================================
-- 5. ai_conversations —— 智能体对话记录（健康报告页用）
-- ================================================
CREATE TABLE IF NOT EXISTS ai_conversations (
    id                    SERIAL PRIMARY KEY,
    user_id               INT REFERENCES users(id) ON DELETE CASCADE,
    session_id            VARCHAR(100),                  -- 兼容老 API（不要改成 conversation_id）
    conversation_id       VARCHAR(64),                   -- v3.1 UUID
    message               TEXT,
    response              TEXT,
    user_choice           VARCHAR(20),
    day_index             INT,
    mode                  VARCHAR(20),     -- control | experiment
    training_plan         JSONB,
    meal_plan             JSONB,
    recommendations       JSONB,
    safety_logs           JSONB,
    agent_decisions       JSONB,
    final_report_v3       JSONB,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_id ON ai_conversations(user_id);
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS session_id      VARCHAR(100);
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(64);
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS message         TEXT;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS response        TEXT;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS user_choice     VARCHAR(20);
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS day_index       INT;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS mode            VARCHAR(20);
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS final_report_v3 JSONB;
COMMENT ON COLUMN ai_conversations.id              IS '主键';
COMMENT ON COLUMN ai_conversations.user_id         IS '用户 ID（FK → users.id）';
COMMENT ON COLUMN ai_conversations.session_id      IS '会话 ID（兼容老 API，老代码读这个字段）';
COMMENT ON COLUMN ai_conversations.conversation_id IS '会话 UUID（v3.1 新增）';
COMMENT ON COLUMN ai_conversations.message         IS '用户消息原文';
COMMENT ON COLUMN ai_conversations.response        IS '智能体回复原文';
COMMENT ON COLUMN ai_conversations.user_choice     IS '当日选择：comply / reject（v3.1 新增，驱动仿真核心）';
COMMENT ON COLUMN ai_conversations.day_index       IS 'Day 索引（第几天）';
COMMENT ON COLUMN ai_conversations.mode            IS '模式：control（对照组）/ experiment（实验组）';
COMMENT ON COLUMN ai_conversations.training_plan   IS 'v3.1 training_plan JSON（运动计划）';
COMMENT ON COLUMN ai_conversations.meal_plan       IS 'v3.1 diet_plan JSON（饮食计划）';
COMMENT ON COLUMN ai_conversations.recommendations IS 'v3.1 recommendations JSON（含 vocal_narrative + sleep_advice 等）';
COMMENT ON COLUMN ai_conversations.safety_logs     IS 'v3.1 safety_result JSON（安全审计产出）';
COMMENT ON COLUMN ai_conversations.agent_decisions IS 'v3.1 reasoning_chain + agent_outputs + derived_metrics';
COMMENT ON COLUMN ai_conversations.final_report_v3 IS 'v3.1 协议形 report（前端 /report/latest 直接读）';
COMMENT ON COLUMN ai_conversations.created_at      IS '会话时间';

-- ================================================
-- 6. user_plans —— 每日计划（v3.1 Table A）= 3 个页面的计划源
--    JSONB 存 training_plan / sleep_plan / diet_plan
-- ================================================
CREATE TABLE IF NOT EXISTS user_plans (
    id              SERIAL PRIMARY KEY,
    user_id         INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_date       DATE NOT NULL,
    training_plan   JSONB,            -- 3.1 training_plan（运动页计划源）
    sleep_plan      JSONB,            -- 3.1 sleep_plan（睡眠页计划源）
    diet_plan       JSONB,            -- 3.1 diet_plan（饮食页计划源）
    source          VARCHAR(50) DEFAULT 'agent',  -- agent | simulator
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_plans_user_date UNIQUE (user_id, plan_date)
);
CREATE INDEX IF NOT EXISTS idx_user_plans_user_id  ON user_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plans_date     ON user_plans(plan_date);
COMMENT ON TABLE user_plans IS 'v3.1 Table A —— 智能体输出（每日计划）';
COMMENT ON COLUMN user_plans.id            IS '主键';
COMMENT ON COLUMN user_plans.user_id       IS '用户 ID（FK → users.id）';
COMMENT ON COLUMN user_plans.plan_date     IS '计划执行日（YYYY-MM-DD）';
COMMENT ON COLUMN user_plans.training_plan IS 'v3.1 training_plan JSON：{training_type, reason, target_rpe, exercises[], safety_flags[]}（运动页计划源）';
COMMENT ON COLUMN user_plans.sleep_plan    IS 'v3.1 sleep_plan JSON：{target_bedtime, target_wake_time, target_duration_h, suggestions[]}（睡眠页计划源）';
COMMENT ON COLUMN user_plans.diet_plan     IS 'v3.1 diet_plan JSON：{total_calories_target, macros, meals[], sauce_factor}（饮食页计划源）';
COMMENT ON COLUMN user_plans.source        IS '数据源：agent（智能体）/ simulator（模拟器）';
COMMENT ON COLUMN user_plans.created_at    IS '创建时间';
COMMENT ON COLUMN user_plans.updated_at    IS '更新时间（触发器自动维护）';
DROP TRIGGER IF EXISTS user_plans_set_updated_at ON user_plans;
CREATE TRIGGER user_plans_set_updated_at
    BEFORE UPDATE ON user_plans
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ================================================
-- 7. user_executions —— 每日执行数据包（v3.1 Table B）= 3 个页面的执行源
--    JSONB 存 body_state / cardiovascular / sleep_execution / exercise_execution / diet_execution
-- ================================================
CREATE TABLE IF NOT EXISTS user_executions (
    id                  SERIAL PRIMARY KEY,
    user_id             INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exec_date           DATE NOT NULL,
    user_choice         VARCHAR(20),                          -- comply | reject
    body_state          JSONB,                                 -- 3.1 body_state
    cardiovascular      JSONB,                                 -- 3.1 cardiovascular
    sleep_execution     JSONB,                                 -- 3.1 sleep_execution
    exercise_execution  JSONB,                                 -- 3.1 exercise_execution
    diet_execution      JSONB,                                 -- 3.1 diet_execution
    source              VARCHAR(50) DEFAULT 'simulator',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_executions_user_date UNIQUE (user_id, exec_date)
);
CREATE INDEX IF NOT EXISTS idx_user_executions_user_id  ON user_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_executions_date     ON user_executions(exec_date);
COMMENT ON TABLE user_executions IS 'v3.1 Table B —— 模拟器输出（每日执行）';
COMMENT ON COLUMN user_executions.id                 IS '主键';
COMMENT ON COLUMN user_executions.user_id            IS '用户 ID（FK → users.id）';
COMMENT ON COLUMN user_executions.exec_date          IS '执行日（YYYY-MM-DD）';
COMMENT ON COLUMN user_executions.user_choice        IS '当日选择：comply / reject（驱动仿真核心）';
COMMENT ON COLUMN user_executions.body_state         IS 'v3.1 body_state JSON：{weight_kg, body_fat_pct, body_age, lean_mass_kg}';
COMMENT ON COLUMN user_executions.cardiovascular     IS 'v3.1 cardiovascular JSON：{resting_hr, hrv_rmssd, hrr, hrv_trend_7d}';
COMMENT ON COLUMN user_executions.sleep_execution    IS 'v3.1 sleep_execution JSON：{actual_bedtime, total_sleep_min, sleep_score, deep_sleep_min, ...}';
COMMENT ON COLUMN user_executions.exercise_execution IS 'v3.1 exercise_execution JSON：{actual_duration_min, actual_rpe, avg_hr, peak_hr, ...}';
COMMENT ON COLUMN user_executions.diet_execution     IS 'v3.1 diet_execution JSON：{total_calories_actual, macros_actual, adherence_rate, ...}';
COMMENT ON COLUMN user_executions.source             IS '数据源：simulator / user_input / agent';
COMMENT ON COLUMN user_executions.created_at         IS '入库时间';

-- ================================================
-- 8. sleep_log —— v3.1.1 用户手动录入的睡眠时间
--    弥补 watch_data 缺失（睡眠页录入表单后端落库点）
-- ================================================
CREATE TABLE IF NOT EXISTS sleep_log (
    id              SERIAL PRIMARY KEY,
    user_id         INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sleep_date      DATE NOT NULL,
    bedtime_at      TIMESTAMP NOT NULL,
    wake_time_at    TIMESTAMP NOT NULL,
    source          VARCHAR(20) DEFAULT 'user_input',
    note            TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sleep_log_user_date UNIQUE (user_id, sleep_date),
    CONSTRAINT ck_sleep_log_wake_after_bed CHECK (wake_time_at > bedtime_at)
);
CREATE INDEX IF NOT EXISTS idx_sleep_log_user_id  ON sleep_log(user_id);
CREATE INDEX IF NOT EXISTS idx_sleep_log_date     ON sleep_log(sleep_date);
COMMENT ON TABLE sleep_log IS 'v3.1.1: 用户手动录入的睡眠时间';
COMMENT ON COLUMN sleep_log.id           IS '主键';
COMMENT ON COLUMN sleep_log.user_id      IS '用户 ID（FK → users.id）';
COMMENT ON COLUMN sleep_log.sleep_date   IS '睡眠日（YYYY-MM-DD，通常 = 起床日）';
COMMENT ON COLUMN sleep_log.bedtime_at   IS '入睡时刻（含日期，TIMESTAMP）';
COMMENT ON COLUMN sleep_log.wake_time_at IS '起床时刻（含日期，TIMESTAMP，约束 > bedtime_at）';
COMMENT ON COLUMN sleep_log.source       IS '数据源：user_input（手填）/ voice（语音）/ agent（智能体）';
COMMENT ON COLUMN sleep_log.note         IS '用户备注（自由文本）';
COMMENT ON COLUMN sleep_log.created_at   IS '创建时间';
COMMENT ON COLUMN sleep_log.updated_at   IS '更新时间（触发器自动维护）';
DROP TRIGGER IF EXISTS sleep_log_set_updated_at ON sleep_log;
CREATE TRIGGER sleep_log_set_updated_at
    BEFORE UPDATE ON sleep_log
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ================================================
-- 9. 视图 v_today_snapshot：3 个页面一次拉齐
--    JOIN watch_data / exercise_records / nutrition_logs
--    提供 v3.1 协议形数据
-- ================================================
CREATE OR REPLACE VIEW v_today_snapshot AS
SELECT
    u.id                                              AS user_id,
    u.name,
    CURRENT_DATE                                      AS snapshot_date,

    -- 身体状态
    (SELECT weight_kg      FROM users WHERE id = u.id) AS weight_kg,
    (SELECT body_fat_pct   FROM users WHERE id = u.id) AS body_fat_pct,
    (SELECT body_age       FROM users WHERE id = u.id) AS body_age,
    (SELECT muscle_mass_kg FROM users WHERE id = u.id) AS lean_mass_kg,

    -- 心血管（最新 watch_data）
    w.heart_rate_rest                                  AS resting_hr,
    (w.hrv_data->>'rmssd')::FLOAT                     AS hrv_rmssd,
    w.hrr                                              AS hrr,
    w.hrv_trend_7d                                     AS hrv_trend_7d,

    -- 睡眠
    w.actual_bedtime,
    w.actual_wake_time,
    w.total_sleep_min,
    (w.sleep_data->>'sleep_score')::INT               AS sleep_score,
    w.deep_sleep_min,
    w.light_sleep_min,
    w.rem_sleep_min,
    w.awake_min,
    w.sleep_efficiency,
    w.deep_sleep_pct,
    w.rr_intervals,
    w.rr_extraction_window,
    w.nap_min,
    w.nap_score,

    -- 运动
    er.actual_duration_min,
    er.actual_rpe,
    er.avg_hr,
    er.peak_hr,
    er.hr_60s_after,
    er.calories_burned,
    er.completion_rate,
    er.completion_rate_display,
    er.hr_series,
    er.hr_series_timestamps,
    er.user_choice,

    -- 饮食
    nl.total_calories_actual,
    nl.calories_remaining,
    nl.protein_g,
    nl.carbs_g,
    nl.fat_g,
    nl.protein_per_kg,
    nl.adherence_rate,
    nl.narrative,
    nl.meal_breakdown
FROM users u
LEFT JOIN LATERAL (
    SELECT * FROM watch_data
    WHERE user_id = u.id
    ORDER BY date DESC LIMIT 1
) w ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM exercise_records
    WHERE user_id = u.id
    ORDER BY date DESC LIMIT 1
) er ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM nutrition_logs
    WHERE user_id = u.id
    ORDER BY date DESC LIMIT 1
) nl ON TRUE
WHERE u.id IS NOT NULL;

COMMENT ON VIEW v_today_snapshot IS
  'v3.1 协议：3 张原表 JOIN 成单行今日执行数据包，供 /api/* 一次拉齐';

-- ================================================
-- 10. 7 天睡眠趋势视图（v3.1.1 扩展，给 SleepView 用）
-- ================================================
CREATE OR REPLACE VIEW v_sleep_7d AS
SELECT
    user_id,
    date,
    (sleep_data->>'total_hours')::FLOAT AS total_hours,
    (sleep_data->>'sleep_score')::INT   AS sleep_score,
    deep_sleep_min,
    nap_min,
    nap_score
FROM watch_data
WHERE date >= CURRENT_DATE - INTERVAL '6 days'
ORDER BY date ASC;

COMMENT ON VIEW v_sleep_7d IS '近 7 天睡眠趋势（SleepView 双轴图数据源）';

-- ================================================
-- 11. 验证
-- ================================================
DO $$
DECLARE
    users_count      INT;
    watch_count      INT;
    exec_count       INT;
    nutrition_count  INT;
    plans_count      INT;
    exec_pkg_count   INT;
    sleep_log_count  INT;
BEGIN
    SELECT COUNT(*) INTO users_count     FROM users;
    SELECT COUNT(*) INTO watch_count     FROM watch_data;
    SELECT COUNT(*) INTO exec_count      FROM exercise_records;
    SELECT COUNT(*) INTO nutrition_count FROM nutrition_logs;
    SELECT COUNT(*) INTO plans_count     FROM user_plans;
    SELECT COUNT(*) INTO exec_pkg_count  FROM user_executions;
    SELECT COUNT(*) INTO sleep_log_count FROM sleep_log;

    RAISE NOTICE '=== 协议表 v3.1 创建/补全完毕 ===';
    RAISE NOTICE 'users            : % 行', users_count;
    RAISE NOTICE 'watch_data       : % 行（睡眠页数据源）', watch_count;
    RAISE NOTICE 'exercise_records : % 行（运动页数据源）', exec_count;
    RAISE NOTICE 'nutrition_logs   : % 行（饮食页数据源）', nutrition_count;
    RAISE NOTICE 'user_plans       : % 行（v3.1 Table A 计划源）', plans_count;
    RAISE NOTICE 'user_executions  : % 行（v3.1 Table B 执行源）', exec_pkg_count;
    RAISE NOTICE 'sleep_log        : % 行（v3.1.1 录入表）', sleep_log_count;
END $$;
