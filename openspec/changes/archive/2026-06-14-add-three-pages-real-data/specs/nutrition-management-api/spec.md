## MODIFIED Requirements

### Requirement: 今日分餐饮食记录（结构 mock 兜底）
系统 SHALL 按餐别（早餐/午餐/晚餐/加餐）返回当日饮食记录，每餐含时间、合计热量与食物明细（名称、克数、单品热量）。第三层换源后：餐次骨架与每餐汇总取自 `nutrition_logs.meal_breakdown`，食物明细取自 `nutrition_logs.recognized_foods`（结构化数组按 `meal` 分组），`sources` 标 `db`；当无结构化数据时回退 mock 并标 `mock`。食材名对齐前端图标集。

#### Scenario: 返回真实分餐与单品
- **WHEN** 调用 `GET /nutrition/{uid}` 且 `recognized_foods`/`meal_breakdown` 有结构化数据
- **THEN** `meals[]` 以 `meal_breakdown` 为餐次骨架、`recognized_foods` 按餐分组挂 `foods`(name/grams/calories)，`sources` 标 `db`

#### Scenario: 无结构化数据回退
- **WHEN** 当日仅有旧 `nutrition_result` 汇总、无结构化单品
- **THEN** `meals[]` 回退 mock 结构并标 `mock`，页面可渲染

### Requirement: 饮食页运动建议（mock 兜底）
系统 SHALL 返回运动建议：运动类型、运动时长、消耗目标，及推荐动作清单（动作名 + 组数×次数 / 时长）。第三层换源后：优先取 `user_plans.training_plan`（`training_type`/`target_duration_min`/`target_total_kcal`/`exercises[].sets,reps`），`sources` 标 `db`；无计划时规则兜底标 `derived`。动作名对齐前端图标集。

#### Scenario: 运动建议来自计划表
- **WHEN** 调用 `GET /nutrition/{uid}` 且当日 `user_plans.training_plan` 存在
- **THEN** `exercise_advice` 的类型/时长/消耗/动作组次取自计划，`sources` 标 `db`

#### Scenario: 无计划回退
- **WHEN** 当日无 `user_plans`
- **THEN** `exercise_advice` 规则兜底并标 `derived`，端点不报错
