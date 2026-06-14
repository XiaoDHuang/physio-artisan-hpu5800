## Why

第三层换源后，三页的"建议 / 训练方案"读 `user_plans`（当前由 seed 预写）。本变更让 **`/plan` 跑出的实时 agent 产出落库到 `user_plans`**，使"点生成报告 → 三页建议/方案随之刷新成本次 AI 决策"，并为后续 v3.1 计划-执行闭环打底。

属**可选增强**：不做不影响现有演示（seed 计划已够）；做了让计划从静态变实时。与第三层解耦、单独成变更，避免污染换源边界（第三层刻意未改 `langgraph_agents.py`）。

## What Changes

- 新增 **adapter**：把 `run_health_assessment` 结果中的 `training_plan / sleep_advice / meal_plan / safety_result` **映射成 v3.1 `user_plans` 协议形**（即三页现在解析的形状），解决 agent 输出形状 ≠ v3.1 计划形状的不一致。
- 新增落库函数（如 `store.postgres_store.save_user_plan(user_id, plan_date, result)`），按 `(user_id, plan_date)` **幂等 UPSERT** 进 `user_plans`（`training_plan/sleep_plan/diet_plan`）。
- 在报告任务终点（`api_server.run_assessment_task`，与 `save_assessment_artifacts` 同处）调用该函数；`plan_date = 当日`。
- 可选：把协议形报告写入 `ai_conversations.final_report_v3`。
- 安全熔断场景（`safety_result.status='blocked'`）：写入带 `safety_flags=[{level:'block'}]` 的最小计划或跳过，不污染页面。

> 非目标：**不含 `user_executions` / 仿真器 R1~R5**（那是"模拟器执行"线，语义不同，另立变更）；不改前端、不改三页取数逻辑（它们已按 v3.1 形状读 `user_plans`）；不改五个 agent 节点本身（仅在 flow 终点加落库）。

## Capabilities

### New Capabilities
- `agent-plan-writeback`: `/plan` 报告产出经 adapter 映射为 v3.1 计划形并幂等落库 `user_plans`，使三页建议/方案读到实时 agent 决策。

### Modified Capabilities
<!-- 无：sleep/exercise/nutrition-management-api 已在第三层改为读 user_plans，本变更只改变其数据来源(seed→agent 实时)，不改需求。 -->

## Impact

- **代码**：`backend/store/postgres_store.py`（新增 `save_user_plan` + adapter，或单列 `agents/plan_adapter.py`）；`backend/api_server.py`（`run_assessment_task` 调用）。
- **数据**：写 `user_plans`（幂等 UPSERT）、可选 `ai_conversations.final_report_v3`；不动 watch/exercise/nutrition。
- **前端**：无改动。
- **多智能体**：`langgraph_agents.py` 节点不改；仅消费其返回结果。
- **依赖**：无新增。
