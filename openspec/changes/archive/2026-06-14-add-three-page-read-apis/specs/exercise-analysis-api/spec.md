## ADDED Requirements

### Requirement: 运动分析页只读聚合端点
系统 SHALL 提供 `GET /exercise/{user_id}` 端点，纯数据库 + mock 聚合（不触发多智能体工作流），一次性返回运动分析页所需的全部结构化数据，毫秒级返回。响应顶层 SHALL 包含 `user_id`、`exercise`（页面数据对象）、`sources`（逐字段来源标注）。

#### Scenario: 存在运动与穿戴数据
- **WHEN** 调用 `GET /exercise/1` 且该用户存在 `watch_data` 记录
- **THEN** 返回 200，`exercise.today_overview` 含 `steps`、`calories_burned`、`duration_minutes`、`intensity` 及各自目标值
- **AND** 真实取到的字段在 `sources` 标为 `db`，目标值来自 `users.goals`

#### Scenario: 无数据回退
- **WHEN** 该用户在 `watch_data`/`exercise_records` 无记录
- **THEN** 返回 200，相关字段回退 mock 并在 `sources` 标为 `mock`，端点不报错

### Requirement: 今日状态汇总
系统 SHALL 返回"今日状态"三行：饮食情况、睡眠情况、身体疲劳度，各含一个状态等级与一句摘要。疲劳度 SHALL 复用既有生理派生（`compute_metrics` 的 `fatigue`：high/medium/low）。

#### Scenario: 返回三行状态
- **WHEN** 调用 `GET /exercise/{uid}`
- **THEN** `exercise.today_status` 含 `diet`(等级+已摄入/目标)、`sleep`(等级+时长)、`fatigue`(等级+建议)
- **AND** `fatigue` 等级在 `sources` 标为 `derived`

### Requirement: 今日运动记录（部分字段 mock）
系统 SHALL 返回当日多条运动记录，每条含运动类型、时长、消耗（取自 `exercise_records`）。当前表无字段的"时间段(起止)"与"距离(公里)" SHALL 由 mock 兜底并在 `sources` 标为 `mock`。

#### Scenario: 存在当日运动记录
- **WHEN** 该用户当日 `exercise_records` 有一条或多条
- **THEN** `exercise.today_records` 为数组，每项含 `exercise_type`、`duration_minutes`、`calories`（`db`）与 `time_range`、`distance_km`（`mock`）

#### Scenario: 当日无运动记录
- **WHEN** 该用户当日无 `exercise_records`
- **THEN** `exercise.today_records` 返回空数组（不报错）

### Requirement: 本周运动趋势
系统 SHALL 返回近 7 天逐日步数序列与步数目标线，供前端绘制柱状趋势。

#### Scenario: 返回 7 天步数趋势
- **WHEN** 调用 `GET /exercise/{uid}`
- **THEN** `exercise.week_trend` 返回最多 7 个数据点（`date`+`steps`）并附 `steps_goal`

### Requirement: 今日运动建议与成就（mock 兜底）
系统 SHALL 返回运动/饮食/睡眠三段建议文本，以及"成就"信息（如超越用户百分位）。建议文本本期由规则/mock 产出；成就百分位需跨用户统计，本期为 mock。二者均在 `sources` 标为 `mock`。

#### Scenario: 返回建议与成就
- **WHEN** 调用 `GET /exercise/{uid}`
- **THEN** `exercise.advice` 含 `exercise`/`nutrition`/`sleep` 三段文本，`exercise.achievement` 含 `percentile` 与文案，均标为 `mock`
