# nutrition-management-api Specification

## Purpose
TBD - created by archiving change add-three-page-read-apis. Update Purpose after archive.
## Requirements
### Requirement: 饮食管理页只读聚合端点
系统 SHALL 提供 `GET /nutrition/{user_id}` 端点，支持查询参数 `date`（默认今天），纯数据库 + mock 聚合（不触发多智能体工作流），一次性返回饮食管理页所需的全部结构化数据。响应顶层 SHALL 包含 `user_id`、`date`、`nutrition`（页面数据对象）、`sources`（逐字段来源标注）。

#### Scenario: 查询指定日期
- **WHEN** 调用 `GET /nutrition/1?date=2026-06-01`
- **THEN** 返回 200 且 `date` 回显 `2026-06-01`，聚合该日 `nutrition_logs`

#### Scenario: 不带日期参数
- **WHEN** 调用 `GET /nutrition/1`（不带 date）
- **THEN** `date` 取今天，聚合当日数据

### Requirement: 每日能量目标 KPI
系统 SHALL 返回顶部四项 KPI：每日目标热量、已摄入热量、还可摄入热量、达成率。目标取自 `users.goals.calorie_intake_target`，已摄入取自当日 `nutrition_logs.nutrition_result.total_calories`，其余两项派生。

#### Scenario: 返回四项 KPI
- **WHEN** 调用 `GET /nutrition/{uid}`
- **THEN** `nutrition.kpi` 含 `goal_calories`(db)、`intake_calories`(db)、`remaining_calories`(derived)、`achievement_rate`(derived)

### Requirement: 能量摄入概览
系统 SHALL 返回当日总能量、三大宏量（碳水/蛋白质/脂肪 的克数、热量、占比），以及推荐摄入、基础代谢(BMR)、运动消耗、能量缺口。宏量与占比取自/派生自 `nutrition_logs`，BMR 由 `health_tools` 派生，运动消耗取自 `watch_data.calories_burned`。

#### Scenario: 返回能量概览
- **WHEN** 调用 `GET /nutrition/{uid}`
- **THEN** `nutrition.energy` 含 `total_calories`、`macros`(carbs/protein/fat 各含 grams/calories/percent)、`recommended_calories`、`bmr`、`exercise_burn`、`energy_gap`
- **AND** `bmr`/`energy_gap`/`macros.*.percent` 在 `sources` 标为 `derived`

### Requirement: 今日分餐饮食记录
系统 SHALL 按餐别（早餐/午餐/晚餐/加餐）返回当日饮食记录，每餐含时间、合计热量与食物明细（名称、克数、单品热量）。第三层换源后：餐次骨架与每餐汇总取自 `nutrition_logs.meal_breakdown`，食物明细取自 `nutrition_logs.recognized_foods`（结构化数组按 `meal` 分组），`sources` 标 `db`；当无结构化数据时回退 mock 并标 `mock`。食材名对齐前端图标集。

#### Scenario: 返回真实分餐与单品
- **WHEN** 调用 `GET /nutrition/{uid}` 且 `recognized_foods`/`meal_breakdown` 有结构化数据
- **THEN** `meals[]` 以 `meal_breakdown` 为餐次骨架、`recognized_foods` 按餐分组挂 `foods`(name/grams/calories)，`sources` 标 `db`

#### Scenario: 无结构化数据回退
- **WHEN** 当日仅有旧 `nutrition_result` 汇总、无结构化单品
- **THEN** `meals[]` 回退 mock 结构并标 `mock`，页面可渲染

### Requirement: 饮食页运动建议
系统 SHALL 返回运动建议：运动类型、运动时长、消耗目标，及推荐动作清单（动作名 + 组数×次数 / 时长）。第三层换源后：优先取 `user_plans.training_plan`（`training_type`/`target_duration_min`/`target_total_kcal`/`exercises[].sets,reps`），`sources` 标 `db`；无计划时规则兜底标 `derived`。动作名对齐前端图标集。

#### Scenario: 运动建议来自计划表
- **WHEN** 调用 `GET /nutrition/{uid}` 且当日 `user_plans.training_plan` 存在
- **THEN** `exercise_advice` 的类型/时长/消耗/动作组次取自计划，`sources` 标 `db`

#### Scenario: 无计划回退
- **WHEN** 当日无 `user_plans`
- **THEN** `exercise_advice` 规则兜底并标 `derived`，端点不报错

