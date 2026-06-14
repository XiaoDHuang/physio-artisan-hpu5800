## MODIFIED Requirements

### Requirement: 今日运动记录（部分字段 mock）
系统 SHALL 返回当日多条运动记录，每条含运动类型、时长、消耗、时间段、距离。第三层换源后：时长/消耗优先取 `exercise_records` 结构化列（`actual_duration_min`/`calories_burned`，缺失回退 `analysis_result` 同义键）；时间段取 `start_time`–`end_time`、距离取 `distance_km`（新列），`sources` 标 `db`；当列为空时回退 mock 并标 `mock`。

#### Scenario: 存在当日运动记录（真实列）
- **WHEN** 该用户当日 `exercise_records` 有记录且填了起止时间/距离
- **THEN** `today_records[]` 的 `time_range`/`distance_km`/`duration_minutes`/`calories` 取自真实列，`sources` 标 `db`

#### Scenario: 当日无运动记录
- **WHEN** 该用户当日无 `exercise_records`
- **THEN** `today_records` 返回空数组（不报错）

### Requirement: 今日运动建议与成就（mock 兜底）
系统 SHALL 返回运动/饮食/睡眠三段建议文本与"成就"信息。第三层换源后：建议优先取 `user_plans`（`training_plan.reason` / `sleep_plan` / `diet_plan.notes`，无则规则派生，标 `derived`）；成就 `percentile` 由跨用户综合分排名聚合查询得出（标 `derived`），无多用户数据时回退 mock。

#### Scenario: 建议来自计划、成就来自聚合
- **WHEN** 调用 `GET /exercise/{uid}` 且存在 `user_plans` 与多用户数据
- **THEN** `advice.*` 取自计划（`sources` 标 `db`/`derived`），`achievement.percentile` 为跨用户排名（`sources` 标 `derived`）

#### Scenario: 数据不足回退
- **WHEN** 无计划或仅单用户
- **THEN** 建议规则派生、成就回退 mock，端点不报错
