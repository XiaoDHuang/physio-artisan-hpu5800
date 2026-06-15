# 实施任务（第一层·后端契约+mock）

> 交付方：deepseek 编码。约束：仅后端，不碰前端、不改表(无 DDL)、不接真实视觉/LLM。
> 运行环境：conda `HPU-3.12`。每个端点均复用 `backend/agents/health_data.py` 既有工具。

## 1. 聚合层公共基础（health_data.py）

- [x] 1.1 在 `health_data.py` 约定统一的来源标注辅助（如 `_mark(sources, field, src)`），`src ∈ {db, mock, derived}`，供三页聚合复用
- [x] 1.2 抽出 `users.goals` 读取与缺省常量兜底（`steps_goal`/`exercise_minutes_goal`/`calorie_intake_target`/`calorie_burn_target`/睡眠区间 7-9h、小憩 20-30m），对齐设计图缺省值
- [x] 1.3 抽出近 N 天 `watch_data` 序列查询（支持 7/14 天），供睡眠趋势与本周步数趋势复用

## 2. 睡眠监测聚合（spec: sleep-monitoring-api）

- [x] 2.1 实现 `get_sleep_overview(uid, range_days=7)`：`today`(sleep_score/grade/total_hours/deep_sleep_hours/nap_minutes/bedtime/wake_time)、`duration`/`nap` 区间与达标状态、`trend[]`、`advice`、`foods`，并填 `sources`
- [x] 2.2 `deep_sleep_hours` 由 `deep_sleep_percent×total_hours` 派生；`grade`/`status` 由分值/区间派生（标 derived）
- [x] 2.3 无 `watch_data` 时回退 mock 场景值（标 mock）；建议文本与推荐/避免食物清单走 mock
- [x] 2.4 实现 `save_sleep_entry(uid, bedtime, wake_time, nap_minutes=None, on_date=None)`：upsert 进对应日期 `watch_data.sleep_data` JSONB（合并键 bedtime/wake_time/nap_minutes/派生 total_hours），无行则插入最小行；无 DDL

## 3. 运动分析聚合（spec: exercise-analysis-api）

- [x] 3.1 实现 `get_exercise_overview(uid)`：`today_overview`(steps/calories_burned/duration_minutes/intensity + 目标)、`today_status`(diet/sleep/fatigue)、`today_records[]`、`week_trend[]`、`advice`、`achievement`，并填 `sources`
- [x] 3.2 `today_status.fatigue` 复用 `compute_metrics(...)['derived']['fatigue']`；`intensity` 沿用 `get_week_overview` 的高/中/低规则（标 derived）
- [x] 3.3 `today_records` 从当日多行 `exercise_records.analysis_result` 取 type/duration/calories（db），`time_range`/`distance_km` mock 兜底；无记录返回空数组
- [x] 3.4 `advice` 三段文本与 `achievement.percentile` 走 mock（标 mock）

## 4. 饮食管理聚合（spec: nutrition-management-api）

- [x] 4.1 实现 `get_nutrition_overview(uid, on_date=None)`：默认今天，`date` 回显；`kpi`(goal/intake/remaining/achievement_rate)、`energy`、`meals[]`、`exercise_advice`，并填 `sources`
- [x] 4.2 `energy`：total + macros(grams/calories/percent)、recommended、`bmr`(health_tools 派生)、`exercise_burn`(watch_data)、`energy_gap`(派生)
- [x] 4.3 `meals[]` 分餐(早/午/晚/加餐)+食物明细(name/grams/calories) 本期 mock 结构兜底（标 mock）；可真取的餐别/日期标 db
- [x] 4.4 `exercise_advice`(training_type/duration/calorie_target/exercises 组次) 走 mock（标 mock）
- [x] 4.5 指定 `date` 无数据日返回空结构 + mock 兜底（页面可渲染，不 404）

## 5. 路由接入（api_server.py）

- [x] 5.1 新增 `GET /sleep/{user_id}`（含 `range` 查询参数），薄路由 `asyncio.to_thread` 调 `get_sleep_overview`
- [x] 5.2 新增 `POST /sleep/entry`（Pydantic 入参校验 bedtime/wake_time 必填、nap_minutes 可选），调 `save_sleep_entry`，缺必填返回 4xx 不写库
- [x] 5.3 新增 `GET /exercise/{user_id}`，调 `get_exercise_overview`
- [x] 5.4 新增 `GET /nutrition/{user_id}`（含 `date` 查询参数），调 `get_nutrition_overview`
- [x] 5.5 在 `/` root 端点的 endpoints 列表登记三页新端点

## 6. 契约文档与自测

- [x] 6.1 更新 `docs/接口契约.md`：新增睡眠/运动/饮食三页端点与字段表，逐字段标 db/mock/derived 与缺口说明
- [x] 6.2 用 `HPU-3.12` 跑通本地自测：`/sleep/1`、`/sleep/1?range=14d`、`POST /sleep/entry`、`/exercise/1`、`/nutrition/1?date=...` 均 200 且字段/`sources` 与 spec 一致；user=2 恶化周可对比
- [x] 6.3 校验三页 mock 字段均带 `sources=mock`，确认第三层换源时前端契约不变
