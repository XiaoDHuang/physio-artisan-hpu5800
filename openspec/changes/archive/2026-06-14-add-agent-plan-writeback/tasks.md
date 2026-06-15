# 实施任务（可选增强·agent 计划写回 user_plans）

> 交付方：deepseek 编码。约束：不改前端、不改三页取数逻辑、不改 langgraph_agents 节点、不写 user_executions/仿真器。
> 依据：本变更 design.md（adapter 映射表 + 落库点 + 幂等/安全规则）。环境 conda HPU-3.12。

## 1. Adapter（agents/plan_adapter.py，纯函数 + 容错）

- [x] 1.1 新建 `to_user_plans(result: dict, plan_date: str) -> {"training_plan","sleep_plan","diet_plan"}`，全程 `.get()` 容错、缺失给 null/默认
- [x] 1.2 工具 `_parse_range_upper(s)`：把 "40-60"/"320-450" 解析为上界/中值 int，失败→None
- [x] 1.3 training_plan 映射：training_type/reason/target_duration_min(解析 recommended_duration)/target_total_kcal(解析 calorie_target)/exercises[](name + sets&reps 或 duration=duration_sec//60 分钟 + intensity + external_id)/safety_flags(blocked→[{level:block}])
- [x] 1.4 sleep_plan 映射：suggestions=[{title: sleep_advice.focus, category:"routine", action: sleep_advice.advice}]（focus 空→advice 首句截断兜底）
- [x] 1.5 diet_plan 映射：total_calories_target/macros{protein_g=protein_target_g,carbs_g/fat_g null}/meals[](grams→amount_g + external_id)/notes=diet_suggestion/sauce_factor=sauce_compensation
- [x] 1.6 保证三页所需字段非空：exercises 强保底(sets=3,reps=12)、suggestions.title fallback、diet_plan.notes fallback

## 2. 落库（store/postgres_store.py）

- [x] 2.1 `_save_user_plan_sync` + `save_user_plan`：调 `to_user_plans`，按 `(user_id, plan_date)` 幂等 `INSERT ON CONFLICT DO UPDATE`
- [x] 2.2 （可选·未做）写 `ai_conversations.final_report_v3`
- [x] 2.3 异常仅 `logger.error`，`return False` 不抛（不影响报告主流程）

## 3. 接入点（api_server.py）

- [x] 3.1 `run_assessment_task` 成功分支，`save_assessment_artifacts` 之后追加 `await save_user_plan(user_id, date.today(), result)`
- [x] 3.2 `plan_date = today`（与三页"最新计划"读取一致）

## 4. 自测与验收（HPU-3.12，先重启 api_server）

- [x] 4.1 `/plan {user_id:1, mode:control}` → `/status` 完成；查 `user_plans` 当日行已被 agent 产出覆盖（source=agent）
- [x] 4.2 `/sleep/1`、`/exercise/1`、`/nutrition/1`：建议/方案变为本次 agent 内容（sources 对应 db/derived），`exercise_advice.exercises[]` 含 name + 组次/时长
- [x] 4.3 再次 `/plan` 幂等：当日仅一行、被覆盖
- [x] 4.4 mode=experiment 同样可写；safety 命中场景 training_plan.safety_flags 含 block
- [x] 4.5 回归：多智能体链路、/report/latest、三页在"无当日 plan"时仍回退 seed 计划
