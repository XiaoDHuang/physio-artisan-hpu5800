## ADDED Requirements

### Requirement: v3.1 对齐的表结构基线
系统 SHALL 以数据协议 v3.1 的 `tables_v3.1_full.sql` 为表结构基线，并提供幂等迁移 `backend/sql/migrate_v3_1_aligned.sql` 补齐 v3.1 全新建表遗漏的兼容列与本项目缺口列；两条建库路径（现有库增量 / 全新库）SHALL 收敛到同一结构。所有 DDL 均 `IF NOT EXISTS`，可重复执行。

#### Scenario: 全新库补回兼容列
- **WHEN** 从零执行 `tables_v3.1_full.sql` 后再执行 `migrate_v3_1_aligned.sql`
- **THEN** `users.goals`、`ai_conversations.messages`、`ai_conversations.speech_report` 均存在（避免与现有库分叉、避免会话历史/报告落库代码报错）

#### Scenario: 现有库增量执行零破坏
- **WHEN** 在现有库执行上述迁移
- **THEN** 仅新增列/表（加法），旧列与旧 JSONB 镜像（sleep_data/analysis_result/nutrition_result）保持不变，现有端点照常工作

### Requirement: 运动记录时间段与距离列
系统 SHALL 为 `exercise_records` 增加 `start_time TIME` / `end_time TIME` / `distance_km FLOAT`，承载运动记录的时间段与距离（v3.1 未覆盖）。

#### Scenario: 运动记录可存时间段与距离
- **WHEN** 写入一条运动记录并填入起止时间与距离
- **THEN** `GET /exercise/{uid}` 的 `today_records[].time_range`/`distance_km` 取自这些列，`sources` 标 `db`

### Requirement: canonical 存储与双写约定
三页取数主源 SHALL 为 v3.1 结构化列；旧 JSONB 镜像（`sleep_data`/`analysis_result`/`nutrition_result`）SHALL 保留供报告 agent 与历史兼容。写入侧 SHALL 以结构化列为准并同步写镜像；读取 SHALL 优先结构化列、缺失回退镜像同义键。

#### Scenario: 读优先结构化列回退镜像
- **WHEN** 某记录结构化列为空但 JSONB 镜像有值
- **THEN** 聚合层回退读镜像同义键（如 `actual_duration_min` 缺失则读 `analysis_result.duration_minutes`），不报错

### Requirement: 睡眠录入真值源为 sleep_log
系统 SHALL 以 `sleep_log` 表为用户手动录入睡眠时间的真值源；录入时按 `(user_id, sleep_date)` upsert，并回灌 `watch_data`（`actual_bedtime`/`actual_wake_time`/`nap_min` + `sleep_data` 镜像）以保持读取兼容。

#### Scenario: 录入写 sleep_log 并回灌 watch_data
- **WHEN** `POST /sleep/entry` 提交入睡/起床时间
- **THEN** `sleep_log` 落一行（wake_time_at > bedtime_at），且 `watch_data` 对应日期回灌入睡/起床/总时长，`GET /sleep/{uid}` 能读到
