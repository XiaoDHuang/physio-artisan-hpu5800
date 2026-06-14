## Context

`/plan` → `LangGraphHealthAgents.run_health_assessment()` 返回（见 langgraph_agents.py）：
```
result = {
  training_plan: {training_type, exercises:[{name,muscles,description,sets,reps?,duration_sec?}],
                  reason, recommended_duration("40-60"), calorie_target("320-450"), source},
  meal_plan:     {total_calories, protein_target_g, diet_suggestion,
                  meals:[{meal,time,total_calories,foods:[{name,grams,calories,protein}]}],
                  day_total_calories, day_total_protein, sauce_compensation, source},
  sleep_advice:  {advice, focus, source},
  safety_result: {status:'passed'|'blocked', ...},
  final_report:  {visual_metrics, vocal_narrative, chart_data, safety_blocked?},
  ...
}
```
三页第三层换源后读 `user_plans`（v3.1 协议形）：sleep/exercise 页读 `training_plan.reason`、`sleep_plan.suggestions[].title`、`diet_plan.notes`；nutrition 页读 `training_plan.{training_type,target_duration_min,target_total_kcal,exercises[].name/sets/reps/duration}`。

**问题**：agent 输出形状 ≠ v3.1 计划形状（也≠三页解析形状）。本变更用 adapter 抹平。

## Goals / Non-Goals

**Goals**：`/plan` 实时产出经 adapter 落库 `user_plans`，三页读到当次 AI 决策；幂等、可重复 /plan。
**Non-Goals**：不含 `user_executions`/仿真器；不改前端/三页取数；不改 agent 节点；不改 watch/exercise/nutrition 表。

## Decisions

- **D1 落库点**：报告成功后，在 `api_server.run_assessment_task`（已调 `save_assessment_artifacts` 处）追加 `save_user_plan(user_id, plan_date, result)`；`plan_date = date.today()`。
- **D2 幂等**：`user_plans` 有 `uq(user_id, plan_date)`，用 `ON CONFLICT (user_id, plan_date) DO UPDATE`。重复 /plan 覆盖当日计划。
- **D3 adapter 独立**：放 `backend/agents/plan_adapter.py`（纯函数 `to_user_plans(result, plan_date) -> {training_plan, sleep_plan, diet_plan}`），便于单测、与落库解耦。
- **D4 安全熔断**：`safety_result.status=='blocked'` 时，`training_plan.safety_flags=[{level:'block', message: 就医分流话术}]`，其余字段尽量保留；仍写库（页面可按 safety_flags 提示）。
- **D5 final_report_v3（可选）**：把 `result`（或其精简协议形）写 `ai_conversations.final_report_v3`，供 `/report/latest` 直读 v3.1 形。本变更可只做 user_plans，final_report_v3 标可选。
- **D6 不写 user_executions**：执行数据是模拟器产物；agent 决策只属 Table A(plan)。

## Adapter 映射（agent result → v3.1 user_plans）

### training_plan（v3.1）
| v3.1 字段 | 来源 / 规则 |
|---|---|
| date | plan_date |
| training_type | `result.training_plan.training_type`（agent 已是 recovery/strength/maintain…；maintain→strength 归一可选）|
| reason | `result.training_plan.reason` |
| target_duration_min | 解析 `recommended_duration`("40-60"→取上界 60 或中值)；解析失败→null |
| target_total_kcal | 解析 `calorie_target`("320-450"→上界/中值)；失败→null |
| target_rpe | `result.derived_metrics`/physio 若有则取，否则 null |
| exercises[] | map 每项：`{name, sets, reps(若有), duration(=duration_sec//60+"分钟" 若有), intensity:"medium", external_id:(若 agent 保留 wger id 则带，否则 null), external_source:"wger"}` |
| safety_flags | blocked→`[{level:"block","message":就医话术}]`，否则 `[]` |

> nutrition 页 `exercise_advice` 据此渲染：`training_type / duration(由 target_duration_min 拼) / calorie_target(=target_total_kcal) / exercises[name + sets×reps 或 duration]`。务必保证 `exercises[]` 至少含 name + (sets&reps 或 duration)。

### sleep_plan（v3.1）
| v3.1 字段 | 来源 / 规则 |
|---|---|
| date | plan_date |
| suggestions[] | 由 `sleep_advice` 包装：`[{title: sleep_advice.focus, category:"routine", action: sleep_advice.advice}]`（focus 为空则用 advice 首句）|
| target_bedtime/target_wake_time/target_duration_h/target_sleep_score | agent 无对应 → null（页面不读这些，安全）|

> sleep/exercise 页 advice 读 `suggestions[].title`，故 `title` 必须有意义（用 focus）。

### diet_plan（v3.1）
| v3.1 字段 | 来源 / 规则 |
|---|---|
| date | plan_date |
| total_calories_target | `meal_plan.total_calories` |
| macros | `{protein_g: meal_plan.protein_target_g, carbs_g: null/派生, fat_g: null/派生}`（agent 仅给蛋白目标；碳水/脂肪可由 total 与蛋白派生或 null）|
| meals[] | map `meal_plan.meals`：`[{meal, foods:[{name, amount_g: grams, calories, protein_g: protein}]}]`（grams→amount_g）|
| notes | `meal_plan.diet_suggestion` |
| sauce_compensation_applied | `meal_plan.sauce_compensation > 1.0` |
| sauce_factor | `meal_plan.sauce_compensation` |

> exercise 页 advice.nutrition 读 `diet_plan.notes`，故 notes 必填（用 diet_suggestion）。

## Risks / Trade-offs
- [agent 输出键/形状可能与上表略有出入] → adapter 用 `.get(...)` 容错 + 缺失给 null/默认；落库前 schema 自检；保留 seed 兜底（无 /plan 时仍读 seed 计划）。
- [/plan 覆盖当日 seed 计划] → 这是预期（实时优先）；非报告日仍用 seed。
- [recommended_duration/calorie_target 是区间字符串] → 提供 `_parse_range_upper()` 工具，解析失败回退 null，页面有默认显示。
- [maintain 训练类型不在 v3.1 枚举] → 归一到 strength/endurance（或保留，页面只展示文本，不强校验）。

## Migration Plan
- 纯新增代码 + 写 `user_plans`（已存在表）。无 DDL。
- 回滚：移除 `run_assessment_task` 的 `save_user_plan` 调用即可，三页自动回退读 seed 计划。

## Open Questions
1. `plan_date` 用"今天"还是"明天"（报告是"今日决策"还是"明日计划"）？默认今天，与三页"最新计划"读取一致。
2. final_report_v3 是否本变更一并写，还是再拆？默认一并写（低成本）。
3. carbs_g/fat_g 目标：派生（total - 蛋白×4 - 默认脂肪%）还是 null？默认 null（页面三环只用已摄入 macros，不依赖计划 macros）。
