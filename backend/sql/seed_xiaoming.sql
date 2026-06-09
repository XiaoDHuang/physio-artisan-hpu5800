-- ================================================
-- 「暴汗艺术家」演示种子数据 - 小明 对照组(control) vs 实验组(experiment)
-- 用途：让多智能体真正"以数据库为准"运行 mode=control/experiment 两套场景。
-- 执行：psql -U postgres -d hpu_db -f seed_xiaoming.sql
-- 说明：数据对齐设计方案 §2.3 / §8，写入既有表的 JSONB 列，无需改表结构。
--      约定用 date 区分场景：对照组 2026-06-07，实验组 2026-06-10。
--      health_data.py 默认取"最新一行"，因此运行 experiment 前可调整日期或按需筛选。
-- ================================================

-- 1. 确保演示用户 id=1 存在（与设计方案小明画像对齐，30岁/175/80）
INSERT INTO users (id, name, age, gender, height_cm, weight_kg, fitness_level, goal, activity_level)
VALUES (1, '小明', 30, 'male', 175, 80, 'intermediate', 'lose_weight', 'moderate')
ON CONFLICT (id) DO UPDATE
    SET age = EXCLUDED.age, height_cm = EXCLUDED.height_cm,
        weight_kg = EXCLUDED.weight_kg, goal = EXCLUDED.goal;

-- 2. 穿戴数据 watch_data（睡眠/HRV/静息心率）
--    对照组（睡眠差、HRV暴跌、静息心率升高）
INSERT INTO watch_data (user_id, date, heart_rate_rest, heart_rate_avg, hrv_data, sleep_data)
VALUES
(1, DATE '2026-06-07', 75, 95,
    '{"rmssd": 32.0, "sdnn": 30, "lf_hf_ratio": 2.1}',
    '{"sleep_score": 58, "total_hours": 6.7, "deep_sleep_percent": 13}'),
(1, DATE '2026-06-10', 63, 78,
    '{"rmssd": 45.0, "sdnn": 48, "lf_hf_ratio": 1.1}',
    '{"sleep_score": 82, "total_hours": 7.6, "deep_sleep_percent": 20}')
ON CONFLICT DO NOTHING;

-- 3. 运动记录 exercise_records（peak_hr / hr_60s / rpe / duration 存入 analysis_result JSONB）
--    对照组（高强度深蹲，心脏恢复极慢 HRR=12）
INSERT INTO exercise_records (user_id, date, exercise_type, analysis_result, form_quality)
VALUES
(1, DATE '2026-06-07', '大重量深蹲',
    '{"duration_minutes": 90, "peak_hr": 175, "hr_60s": 163, "rpe": 9}', 'fair'),
(1, DATE '2026-06-10', '核心激活+低强度有氧',
    '{"duration_minutes": 30, "peak_hr": 130, "hr_60s": 110, "rpe": 4}', 'good')
ON CONFLICT DO NOTHING;

-- 4. 饮食记录 nutrition_logs（diet_narrative 存入 nutrition_result JSONB）
--    对照组（随意饮食、低蛋白、隐形酱料）
INSERT INTO nutrition_logs (user_id, date, meal_type, nutrition_result)
VALUES
(1, DATE '2026-06-07', 'daily',
    '{"diet_narrative": "早餐：油条2根，甜豆浆。午餐：凯撒沙拉多加酱，红烧肉盖饭。晚餐：炸鸡啤酒，宵夜方便面加火腿肠。"}'),
(1, DATE '2026-06-10', 'daily',
    '{"diet_narrative": "早餐：无糖希腊酸奶200g，坚果，蓝莓。午餐：香煎鸡胸肉150g，糙米饭，水煮西蓝花。晚餐：香煎三文鱼150g，藜麦沙拉。"}')
ON CONFLICT DO NOTHING;

-- ================================================
-- 完成：现在 mode=control 取 2026-06-07 那套；如需 experiment，
--      可在查询层按日期筛选 2026-06-10，或临时删除对照组行。
-- ================================================
