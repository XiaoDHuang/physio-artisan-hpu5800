# 实施任务（可选增强·agent 计划写回 user_plans）

> 交付方：deepseek 编码。约束：不改前端、不改三页取数逻辑、不改 langgraph_agents 节点、不写 user_executions/仿真器。
> 依据：本变更 design.md（adapter 映射表 + 落库点 + 幂等/安全规则）。环境 conda HPU-3.12。

## 1. Adapter（agents/plan_adapter.py，纯函数 + 容错）

- [ ] 1.1 新建 `to_user_plans(result: dict, plan_date: str) -> {"training_plan","sleep_plan","diet_plan"}`，全程 `.get()` 容错、缺失给 null/默认
- [ ] 1.2 工具 `_parse_range_upper(s)`：把 "40-60"/"320-450" 解析为上界/中值 int，失败→None
- [ ] 1.3 training_plan 映射：training_type/reason/target_duration_min(解析 recommended_duration)/target_total_kcal(解析 calorie_target)/exercises[](name + sets&reps 或 duration=duration_sec//60 分钟 + intensity)/safety_flags(blocked→[{level:block}])
- [ ] 1.4 sleep_plan 映射：suggestions=[{title: sleep_advice.focus, category:"routine", action: sleep_advice.advice}]（focus 空→advice 首句）
- [ ] 1.5 diet_plan 映射：total_calories_target/macros{protein_g=protein_target_g,carbs_g,fat_g(可 null)}/meals[](grams→amount_g)/notes=diet_suggestion/sauce_factor=sauce_compensation
- [ ] 1.6 保证三页所需字段非空：training_plan.reason、exercises[](name+组次/时长)、sleep_plan.suggestions[].title、diet_plan.notes

## 2. 落库（store/postgres_store.py）

- [ ] 2.1 新增 `save_user_plan(user_id, plan_date, result)`：调 adapter，`INSERT INTO user_plans(...) ON CONFLICT (user_id, plan_date) DO UPDATE`（幂等），写 training_plan/sleep_plan/diet_plan + source='agent'
- [ ] 2.2 （可选）写 `ai_conversations.final_report_v3 = result(协议形)`（同 session_id 行）
- [ ] 2.3 异常仅 logger 记录，不抛（不影响报告主流程）

## 3. 接入点（api_server.py）

- [ ] 3.1 `run_assessment_task` 报告成功分支，在 `save_assessment_artifacts` 之后追加 `await save_user_plan(user_id, date.today().isoformat(), result)`（异步/to_thread）
- [ ] 3.2 plan_date 用当日（与三页"最新计划"读取一致）

## 4. 自测与验收（HPU-3.12，先重启 api_server）

- [ ] 4.1 `/plan {user_id:1, mode:control}` → `/status` 完成；查 `user_plans` 当日行已被 agent 产出覆盖（source=agent）
- [ ] 4.2 `/sleep/1`、`/exercise/1`、`/nutrition/1`：建议/方案变为本次 agent 内容（sources 对应 db/derived），`exercise_advice.exercises[]` 含 name + 组次/时长
- [ ] 4.3 再次 `/plan` 幂等：当日仅一行、被覆盖
- [ ] 4.4 mode=experiment 同样可写；safety 命中场景 training_plan.safety_flags 含 block
- [ ] 4.5 回归：多智能体链路、/report/latest、三页在"无当日 plan"时仍回退 seed 计划
