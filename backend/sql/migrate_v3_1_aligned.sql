-- ================================================
-- migrate_v3_1_aligned.sql —— v3.1 兼容补丁 + 缺口列
--
-- 用途：在 tables_v3.1_full.sql 之后执行（或独立重跑），为现有库补全
--       三补丁 + 运动缺口列。全部 ADD COLUMN IF NOT EXISTS / CREATE IF NOT EXISTS。
-- 设计依据：openspec/changes/add-three-pages-real-data/design.md
-- ================================================
SET client_min_messages = WARNING;

-- D2 三补丁：v3.1 全新建表漏了这三列（现有库已有则幂等安全）
ALTER TABLE users            ADD COLUMN IF NOT EXISTS goals          JSONB;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS messages       JSONB;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS speech_report  TEXT;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS recommendations JSONB;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_conv_session ON ai_conversations(session_id);

-- 向已存在的 ai_conversations 行填充 migration 标记（无破坏）
COMMENT ON COLUMN ai_conversations.messages       IS '消息历史 JSONB（老列补丁）';
COMMENT ON COLUMN ai_conversations.speech_report  IS '语音报告 TEXT（老列补丁）';

-- D3 运动记录缺口列：时间段 + 距离（v3.1 用 hr_series 时序，未覆盖此三列）
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS start_time   TIME;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS end_time     TIME;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS distance_km  FLOAT;

-- 补 watch_data.sleep_score（tables_v3.1_full.sql 的 CREATE TABLE 含此列，
-- 但 ALTER TABLE 增量段遗漏；现有表无此列则需补上）
ALTER TABLE watch_data ADD COLUMN IF NOT EXISTS sleep_score INT;

COMMENT ON COLUMN exercise_records.start_time  IS '训练开始时间（HH:MM），运动页 time_range 源';
COMMENT ON COLUMN exercise_records.end_time    IS '训练结束时间（HH:MM），运动页 time_range 源';
COMMENT ON COLUMN exercise_records.distance_km IS '训练距离（km），运动页记录';

-- 验证提示（不阻塞）
DO $$
BEGIN
    RAISE NOTICE 'migrate_v3_1_aligned 完成：3 补丁 + 运动缺口列已就绪';
END $$;
