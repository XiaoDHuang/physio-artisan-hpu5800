## ADDED Requirements

### Requirement: /plan 产出落库 user_plans
系统 SHALL 在 `/plan`（多智能体报告）成功产出后，将 `training_plan / sleep_advice / meal_plan / safety_result` 经 adapter 映射为 v3.1 `user_plans` 协议形（`training_plan / sleep_plan / diet_plan`），按 `(user_id, plan_date)` 幂等 UPSERT 落库；`plan_date` 默认当日。落库失败 SHALL 不影响报告主流程（仅记录日志）。

#### Scenario: 报告成功后写入当日计划
- **WHEN** 调用 `/plan` 且报告成功生成
- **THEN** `user_plans` 中该用户当日行被写入/覆盖，含 `training_plan/sleep_plan/diet_plan` 三块（v3.1 协议形）

#### Scenario: 重复 /plan 幂等覆盖
- **WHEN** 同一用户同一天再次 `/plan`
- **THEN** 当日 `user_plans` 行被本次产出覆盖，不产生重复行

#### Scenario: 落库失败不影响报告
- **WHEN** `user_plans` 写入异常
- **THEN** `/plan`/`/status` 仍返回报告结果，仅日志记录写库失败

### Requirement: agent 输出到 v3.1 计划的 adapter 映射
系统 SHALL 提供纯函数 adapter，将 agent 结果映射为三页可解析的 v3.1 计划形，至少保证：`training_plan.reason`、`training_plan.exercises[]`（每项含 `name` 且含 `sets`+`reps` 或 `duration`）、`training_plan.training_type`、`sleep_plan.suggestions[].title`、`diet_plan.notes` 有意义；缺失上游字段时以 `null`/默认兜底，不抛错。

#### Scenario: 三页所需字段齐备
- **WHEN** adapter 处理一份正常 agent 结果
- **THEN** 产出的 `user_plans` 能让 `/sleep`、`/exercise`、`/nutrition` 读到非空的建议文本与训练方案（`exercise_advice.exercises[]` 含 name + 组次或时长）

#### Scenario: 上游字段缺失容错
- **WHEN** agent 结果缺少 `recommended_duration`/`calorie_target` 等区间字段
- **THEN** 对应 `target_duration_min`/`target_total_kcal` 置 `null`，adapter 不抛异常，页面用默认展示

### Requirement: 安全熔断计划标记
当报告 `safety_result.status == "blocked"` 时，系统 SHALL 在落库的 `training_plan.safety_flags` 写入 `[{level:"block", message: 就医分流话术}]`，其余计划字段尽量保留。

#### Scenario: 熔断时带 block 标记落库
- **WHEN** 报告命中安全红线
- **THEN** `user_plans.training_plan.safety_flags` 含一条 `level=block` 记录
