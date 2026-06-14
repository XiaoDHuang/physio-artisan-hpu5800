# 实施任务（第三层·扩表 + mock 换真实源）

> 交付方：deepseek 编码。约束：前端零改动（契约字段名/响应结构不变，仅 `sources` 值变）；DDL 全幂等；读优先结构化列、回退旧 JSONB 镜像。
> 依据：本变更 design.md（迁移 SQL + 换源映射 + JSON 结构 + 写入规则）。运行环境 conda `HPU-3.12`。

## 1. 数据库迁移

- [x] 1.1 将同学的 `docs/backend/tables_v3.1_full.sql` 纳入 `backend/sql/`（或确认放置位置），作为 v3.1 全量基线
- [x] 1.2 新建 `backend/sql/migrate_v3_1_aligned.sql`（见 design「迁移 SQL」）：补 `users.goals`、`ai_conversations.messages`、`ai_conversations.speech_report`、`ai_conversations.recommendations`、`uq_ai_conv_session`；`exercise_records` 加 `start_time`/`end_time`/`distance_km`；全部 `IF NOT EXISTS`
- [x] 1.3 用 `HPU-3.12` 在现有库执行 `tables_v3.1_full.sql` → `migrate_v3_1_aligned.sql`，确认纯加列、现有端点全部不报错

## 2. 取数层换源（backend/agents/health_data.py）

- [x] 2.1 抽 `_pick(col_val, jsonb_get, default)` 回退助手：优先结构化列、缺失回退旧 JSONB 镜像同义键
- [x] 2.2 运动负荷映射换源（`get_health_snapshot`/`compute_metrics`）：`duration_minutes←actual_duration_min`、`hr_60s←hr_60s_after`、`rpe←actual_rpe`、`peak_hr←peak_hr`、`calories←calories_burned`，均回退 `analysis_result` 同义键
- [x] 2.3 `get_sleep_overview` 换源：sleep_score/total_hours(/60)/deep_sleep_hours/nap_minutes/bedtime/wake_time 取结构化列（bedtime/wake 优先 `sleep_log`），trend 走 watch_data 历史；`sources` 改 db/derived
- [x] 2.4 `get_sleep_overview` 建议/食物：advice 取 `user_plans.sleep_plan.suggestions`/`training_plan.reason`（无则规则派生标 derived）；foods 改对齐图标集 curated 常量标 default
- [x] 2.5 `get_exercise_overview` 换源：today_records 取结构化列 + `start_time/end_time`(拼 time_range)/`distance_km`；advice 取 `user_plans`；achievement.percentile 改跨用户综合分排名聚合（标 derived，单用户回退 mock）
- [x] 2.6 `get_nutrition_overview` 换源：intake/macros/remaining 取结构化列（回退 JSONB）；meals[] 以 `meal_breakdown` 为骨架 + `recognized_foods` 按 meal 分组挂 foods；exercise_advice 取 `user_plans.training_plan`（无则规则兜底）
- [x] 2.7 全部 mock 分支保留为"无真实数据时回退"，并把对应 `sources` 由恒 mock 改为 db/derived/default（有真实即标真实）

## 3. 写入路径（backend/agents/intake.py + 录入）

- [x] 3.1 `save_entry("exercise")`：写 `analysis_result`(镜像) + 同步结构化列 `actual_duration_min/peak_hr/hr_60s_after/actual_rpe/calories_burned`
- [x] 3.2 `save_entry("nutrition")`：写 `nutrition_result`(镜像) + 结构化 `total_calories_actual/narrative`
- [x] 3.3 `save_sleep_entry`：改以 `sleep_log` upsert(user_id,sleep_date,bedtime_at,wake_time_at) 为真值源，并回灌 `watch_data`(actual_bedtime/actual_wake_time/nap_min + sleep_data 镜像)；起床早于入睡→422
- [x] 3.4 `_ensure_schema`/启动 DDL 与 `migrate_v3_1_aligned.sql` 对齐（幂等，含 sleep_log/goals/messages/speech_report 兜底）

## 4. 重刷历史数据 —— 已由 Claude 实现并验证：`backend/scripts/seed_week_history_v31.py`

- [x] 4.1-4.5 seed 脚本已包含全部所需数据，已实跑通过

## 5. 契约文档

- [x] 5.1 更新 `docs/接口契约.md` §6/§7：三页各 mock 字段标注改真实来源（db/derived/default），补 `sleep_log`/`user_plans` 来源说明

## 6. 自测与验收

- [x] 6.1 `HPU-3.12` 跑通：`/sleep/1`、`/sleep/1?range=14d`、`POST /sleep/entry`(正常+非法)、`/exercise/1`、`/exercise/3`(goals=NULL 用户)、`/nutrition/1?date=...` 均 200
- [x] 6.2 校验三页原 mock 字段 `sources` 已变 db/derived/default（运动 time_range/distance_km、饮食 meals.foods、建议/方案、睡眠 bedtime/wake/nap）；仍缺数据处回退 mock 不报错
- [x] 6.3 前端四页回归：契约字段不变、页面照常渲染、食物/动作图标对上（因 seed 对齐图标集）
- [x] 6.4 重启后端进程后确认 energy_gap=目标-已摄入 等已生效
