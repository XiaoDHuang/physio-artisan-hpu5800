-- ================================================
-- 迁移：为「健康报告」仪表盘补齐字段
-- 执行：psql -U postgres -d hpu_db -f migrate_dashboard.sql
-- 全部幂等；seed_week_history.py 首次运行时也会自动执行同样 DDL。
-- ================================================

-- 1. 肌肉量（仪表盘"身体指标概览"需要，库内原缺）
ALTER TABLE users ADD COLUMN IF NOT EXISTS muscle_mass_kg FLOAT;

-- 2. 体脂率（上轮已加，幂等重复声明）
ALTER TABLE users ADD COLUMN IF NOT EXISTS body_fat_pct FLOAT;

-- 3. 目标配置（步数目标/运动达标阈值/消耗与摄入目标等，统一一列 JSONB）
--    示例：{"steps_goal":8000,"exercise_minutes_goal":30,"exercise_days_goal":7,
--           "calorie_burn_target":500,"calorie_intake_target":1800,
--           "exercise_duration_target":"40-60","calorie_burn_session_target":"320-450"}
ALTER TABLE users ADD COLUMN IF NOT EXISTS goals JSONB;

-- 说明：以下"补充数据"无需加列，写进既有 JSONB 列即可——
--   · 睡眠分时浅睡/深睡序列 -> watch_data.sleep_data.stages_timeline
--   · 饮食实际摄入(总/碳水/蛋白/脂肪) -> nutrition_logs.nutrition_result
--   · 饮食均衡度 -> nutrition_logs.balance_score（已有列）
-- ================================================
