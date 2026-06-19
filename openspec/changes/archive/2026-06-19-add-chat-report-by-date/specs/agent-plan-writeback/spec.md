# agent-plan-writeback Delta

## MODIFIED Requirements

### Requirement: /plan 产出落库 user_plans

系统 SHALL 在 `/plan`（多智能体报告）成功产出后，将 `training_plan / sleep_advice / meal_plan / safety_result` 经 adapter 映射为 v3.1 `user_plans` 协议形（`training_plan / sleep_plan / diet_plan`），按 `(user_id, plan_date)` 幂等 UPSERT 落库；**`plan_date` 为报告锚点日 `anchor_date`（请求 `date` 或默认今天）**，不得固定为任务执行当日。落库失败 SHALL 不影响报告主流程（仅记录日志）。

#### Scenario: 历史日报告写入对应计划日

- **WHEN** 调用 `/plan` 且 `date=2026-06-10` 报告成功生成
- **THEN** `user_plans` 中 `(user_id, plan_date=2026-06-10)` 行被写入/覆盖

#### Scenario: 重复 /plan 幂等覆盖

- **WHEN** 同一用户同一 `plan_date` 再次 `/plan`
- **THEN** 该 `plan_date` 的 `user_plans` 行被本次产出覆盖，不产生重复行

#### Scenario: 写库失败不阻断报告

- **WHEN** `user_plans` 写入异常
- **THEN** `/plan`/`/status` 仍返回报告结果，仅日志记录写库失败
