## Context

当前库 = `hpu_db.sql`（users/watch_data/exercise_records/nutrition_logs/**ai_conversations(messages,speech_report,...)**/prompt_templates/safety_logs）+ `migrate_chat_unify.sql`(session_id 唯一索引) + `migrate_dashboard.sql`(users.body_fat_pct/muscle_mass_kg/**goals**) + 运行时 `intake._ensure_schema`。

同学的 v3.1（`docs/backend/数据协议 v3.1.md` + `docs/backend/tables_v3.1_full.sql`）对四张核心表 `ADD COLUMN IF NOT EXISTS` 扩列 + 保留旧 JSONB 镜像（`sleep_data/analysis_result/nutrition_result/hrv_data`），并新增 `user_plans`(计划) / `user_executions`(执行) / `sleep_log`(录入) + 视图 `v_today_snapshot`/`v_sleep_7d`。**对现有库纯增量、零破坏。**

三页换源清单见归档变更① `design.md` 的"实现纪要"。

## Goals / Non-Goals

**Goals**
- 采纳 v3.1 表结构；三页 mock 字段换为真实数据（`sources` mock→db/derived）；前端零改动。
- 两条建库路径（现有库增量 / 全新库）收敛到同一结构。

**Non-Goals**
- 不改前端、不改四页 UI；契约字段名与响应结构不变（仅 `sources` 值变）。
- 不实现仿真器 R1~R5 闭环（`user_plans/user_executions` 建表纳入；本层仅"读计划"补建议/方案）。
- 不引入新依赖。

## Decisions

- **D1 canonical 存储**：三页取数**主源 = v3.1 结构化列**；`sleep_data/analysis_result/nutrition_result` JSONB 镜像**保留**（报告 agent + 历史兼容）。写入侧：**结构化列为准 + 同步写镜像**（避免双写分叉）。
- **D2 三补丁**（修复 v3.1 全新建表漏列，与现有库分叉）：补 `users.goals JSONB`、`ai_conversations.messages JSONB`、`ai_conversations.speech_report TEXT`。
- **D3 运动缺口列**：`exercise_records` 加 `start_time TIME` / `end_time TIME` / `distance_km FLOAT`（v3.1 用 hr_series 时序，但我们运动记录需要时间段+距离）。
- **D4 饮食单品**：用 `nutrition_logs.recognized_foods` JSONB（结构化数组）+ `meal_breakdown`（每餐汇总），**不建 meal_items 表**。
- **D5 睡眠录入真值源 = `sleep_log` 表**：`POST /sleep/entry` 写 `sleep_log`（upsert by (user_id, sleep_date)），并回灌 `watch_data`(actual_bedtime/actual_wake_time/nap_min + sleep_data 镜像 total_hours)。
- **D6 建议/训练方案来源**：读 `user_plans`——睡眠建议←`sleep_plan.suggestions`、运动/饮食的训练方案(组次)←`training_plan.exercises[]`、运动页三段建议←`training_plan.reason`+`sleep_plan`+`diet_plan.notes`（无计划则规则兜底，标 `derived`）。
- **D7 成就百分位**：跨用户聚合查询（按综合健康分排名），标 `derived`；无多用户时回退 mock。
- **D8 食物推荐/避免清单**：curated 常量，**对齐前端图标集**（香蕉/燕麦/鸡蛋/牛奶/坚果·咖啡/辛辣食物/油炸食品/甜点/奶茶），标 `default`。

## 迁移 SQL（`backend/sql/migrate_v3_1_aligned.sql`，幂等，现有库执行=纯加列）

> 落地方式：先 `psql -f tables_v3.1_full.sql`（同学全量），再 `psql -f migrate_v3_1_aligned.sql`（本补丁）。本补丁单独可重跑。

```sql
SET client_min_messages = WARNING;

-- D2 三补丁：v3.1 全新建表漏了这三列（现有库已有，幂等安全）
ALTER TABLE users            ADD COLUMN IF NOT EXISTS goals          JSONB;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS messages       JSONB;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS speech_report  TEXT;
ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS recommendations JSONB;  -- 同属老列，确保存在
CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_conv_session ON ai_conversations(session_id);

-- D3 运动记录缺口列：时间段 + 距离
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS start_time   TIME;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS end_time     TIME;
ALTER TABLE exercise_records ADD COLUMN IF NOT EXISTS distance_km  FLOAT;

-- 说明：watch_data/nutrition_logs 的结构化列、user_plans/user_executions/sleep_log/视图
--       均由 tables_v3.1_full.sql 建好，本补丁不重复。
```

## 换源映射（实现据此把 mock→真实，并填 `sources`）

### `GET /sleep/{uid}`（health_data.get_sleep_overview）
| 字段 | 现(mock/JSONB) | 换为 | sources |
|---|---|---|---|
| today.sleep_score | sleep_data.sleep_score | `watch_data.sleep_score`(列，回退 sleep_data) | db |
| today.total_hours | sleep_data.total_hours | `watch_data.total_sleep_min/60`(回退 sleep_data) | db/derived |
| today.deep_sleep_hours | 派生 | `watch_data.deep_sleep_min/60` | derived |
| today.bedtime/wake_time | sleep_data | `sleep_log`(优先) → `watch_data.actual_bedtime/actual_wake_time` | db→mock |
| today.nap_minutes | sleep_data.nap_minutes | `watch_data.nap_min` | db→mock |
| trend[] | watch_data sleep_data | 视图 `v_sleep_7d`（或 watch_data 历史）| db |
| advice.{sleep,nutrition,exercise} | mock | `user_plans.sleep_plan.suggestions`/`training_plan.reason`（无则规则）| db→derived |
| foods.recommended/avoid | mock 不齐 | curated 常量，对齐图标集 | default |

### `GET /exercise/{uid}`（get_exercise_overview）
| 字段 | 现 | 换为 | sources |
|---|---|---|---|
| today_overview.steps/calories_burned/duration_minutes | watch_data 列 | 不变（已 db）| db |
| today_records[].exercise_type/duration_minutes/calories | analysis_result JSONB | `exercise_records.actual_duration_min`/`calories_burned`(回退 analysis_result.duration_minutes/calories) | db |
| today_records[].time_range | mock | `start_time`–`end_time` 拼接 | db→mock |
| today_records[].distance_km | mock | `distance_km` 列 | db→mock |
| today_status.fatigue | derived | 不变（compute_metrics）| derived |
| advice.{exercise,nutrition,sleep} | mock | `user_plans`（reason/suggestions/notes，无则规则）| db→derived |
| achievement.percentile | mock | 跨用户综合分排名聚合 | derived→mock |

> 运动负荷映射（compute_metrics/snapshot 同步换）：`duration_minutes←actual_duration_min`、`peak_hr←peak_hr`、`hr_60s←hr_60s_after`、`rpe←actual_rpe`、`calories←calories_burned`（均回退 analysis_result 同义键）。

### `GET /nutrition/{uid}?date=`（get_nutrition_overview）
| 字段 | 现 | 换为 | sources |
|---|---|---|---|
| kpi.intake_calories / energy.total_calories | nutrition_result.total_calories | `nutrition_logs.total_calories_actual`(回退 nutrition_result) | db |
| energy.macros.{carbs,protein,fat}.grams | nutrition_result.*_g | `nutrition_logs.carbs_g/protein_g/fat_g`(回退 JSONB) | db |
| kpi.remaining_calories | 派生 | `nutrition_logs.calories_remaining`(有则 db，否则派生 goal-intake) | db→derived |
| meals[].meal_type/time/total_calories | mock | `meal_breakdown` JSONB（每餐汇总）| db→mock |
| meals[].foods[].name/grams/calories | mock | `recognized_foods` JSONB（结构化数组，按 meal 分组）| db→mock |
| exercise_advice(类型/时长/消耗/动作组次) | mock | `user_plans.training_plan`(training_type/target_duration_min/target_total_kcal/exercises[sets,reps]) | db→mock |

## 关键 JSON 结构（写入/读取约定）

`nutrition_logs.recognized_foods`（结构化单品，供 meals[].foods）：
```json
[
  {"meal":"早餐","time":"08:30","name":"鸡蛋","grams":100,"calories":155,"protein_g":13,
   "external_id":171477,"external_source":"usda"},
  {"meal":"早餐","time":"08:30","name":"牛奶","grams":200,"calories":104,"protein_g":7}
]
```
`nutrition_logs.meal_breakdown`（每餐汇总，供 meals[] 头部）：
```json
[{"meal":"早餐","time":"08:30","calories":271,"protein_g":20}, {"meal":"午餐", ...}]
```
> meals[] 渲染：以 `meal_breakdown` 为餐次骨架，`recognized_foods` 按 `meal` 分组挂 foods。食材名对齐前端图标集（牛奶/鸡蛋/包子/鸡胸肉/西兰花…）。

## 写入路径改动（intake.py / save_sleep_entry / 录入）

- `intake.save_entry("exercise")`：除写 `analysis_result`(镜像)，同步写结构化列 `actual_duration_min/peak_hr/hr_60s_after/actual_rpe/calories_burned`（+可选 start_time/end_time/distance_km）。
- `intake.save_entry("nutrition")`：除写 `nutrition_result`(镜像)，同步写 `total_calories_actual/protein_g/carbs_g/fat_g` + `recognized_foods`(结构化) + `meal_breakdown`。
- `intake.save_entry("body")`：`users.weight_kg/body_fat_pct/muscle_mass_kg`（不变）。
- `save_sleep_entry`：改写 **`sleep_log`** upsert(user_id,sleep_date,bedtime_at,wake_time_at)，并回灌 `watch_data`(actual_bedtime/actual_wake_time/nap_min + sleep_data 镜像 total_hours/bedtime/wake_time/nap_minutes)，保持 `GET /sleep` 读取兼容。

## Risks / Trade-offs
- [双写镜像分叉] → 统一在 intake/seed 一处双写；读优先结构化列、回退镜像；契约不变。
- [v3.1 全新建表漏 3 列] → 本补丁 ADD COLUMN 修复；CI/部署文档注明"先 full 再 aligned"。
- [运动结构化列名 ≠ 旧 JSONB 键] → health_data 取数做 `结构化列 ?? analysis_result.同义键` 回退，平滑过渡。
- [user_plans 无数据时建议/方案为空] → 规则兜底 + seed 写入演示计划，标 `derived`。
- [seed 重刷影响现有演示] → 幂等删除窗口行后重插；保留 user=1 向好 / user=2 恶化两套。

## Migration Plan
- 顺序：`tables_v3.1_full.sql` → `migrate_v3_1_aligned.sql` → 重刷 `seed_week_history.py`。
- 回滚：新增列/表为加法，回滚只需停用新查询分支（代码回退）；DDL 可保留不影响旧逻辑（旧 JSONB 镜像仍在）。

## Open Questions
1. `user_plans` 的演示数据由 seed 直接写，还是跑一次 `/plan` 由 agent 落库？（倾向 seed 直接写，演示稳定。）
2. `v_today_snapshot`/`v_sleep_7d` 是否直接被 health_data 采用，还是仍走 Python 聚合？（倾向保留 Python 聚合，视图作为对照/备用。）
3. 成就百分位的"综合分"口径（复用 get_week_overview 的 health_score 跨用户排名？）。
