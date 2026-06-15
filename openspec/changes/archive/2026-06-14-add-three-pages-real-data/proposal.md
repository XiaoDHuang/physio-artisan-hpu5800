## Why

变更①②已上线：三页只读端点 + 四页前端，缺失字段以 mock 兜底并带 `sources` 标记。第三层目标：**对齐同学的数据协议 v3.1，扩展表结构，把 mock 字段替换为真实数据**，`sources` 由 `mock`→`db`，前端因只认契约而零改动。

经全盘分析（详见 design.md）：v3.1（`docs/backend/数据协议 v3.1.md` + `docs/backend/tables_v3.1_full.sql`）是「加法式扩列 + 保留旧 JSONB 镜像」，对**现有库**纯增量、零破坏；并用 `user_plans`(计划) / `user_executions`(执行) / `sleep_log`(录入) 三新表，天然补上我们"建议/训练方案/录入"等 agent 产出缺口。

## What Changes

- **采纳 v3.1 为表结构基线**（`tables_v3.1_full.sql` 全量幂等），并打 **3 个兼容补丁**（v3.1 全新建表漏列，会与现有库结构分叉）：
  - `users.goals JSONB`、`ai_conversations.messages JSONB`、`ai_conversations.speech_report TEXT` —— `CREATE` 补回 + `ADD COLUMN IF NOT EXISTS`。
- **补 2 个真覆盖缺口**（v3.1 未覆盖）：
  - `exercise_records` 加 `start_time TIME` / `end_time TIME` / `distance_km FLOAT`（运动记录时间段/距离）。
  - 运动"成就百分位"：跨用户聚合查询实现（不建表）。
- **饮食单品明细**：用 v3.1 已有的 `recognized_foods` JSONB（结构化为 `[{name,grams,calories,protein_g,meal,...}]`）+ `meal_breakdown`（每餐汇总）承载，**不另建 meal_items 表**。
- **聚合层换源**：`health_data.py` 三个 `*_overview` 的 mock 分支替换为真实查询/计划读取，`sources` 标 `db`/`derived`。
- **canonical 约定**：三页取数主源 = v3.1 结构化列；`sleep_data/analysis_result/nutrition_result` JSONB 镜像保留（报告 agent/历史兼容）；写入侧结构化列为准 + 同步镜像；睡眠录入真值源 = `sleep_log` 表。
- **重刷历史**：`seed_week_history.py` 填结构化列 + `recognized_foods` + 同步镜像 + goals 对齐(10000/60/2000/500)，修"仅录睡眠行遮蔽运动总览"。
- **同步契约**：`docs/接口契约.md` 各 mock 字段标注改真实来源。

> 非目标：不改前端（契约字段名/响应结构稳定，仅 `sources` 值变化）；不改四页 UI；不强制接入仿真器闭环（`user_plans/user_executions` 建表纳入，但本层只读"计划"补建议/方案，不实现 R1~R5 仿真）。

## Capabilities

### New Capabilities
- `health-db-schema`: v3.1 对齐的表结构（扩列 + 3 补丁 + 缺口列 + `user_plans/user_executions/sleep_log` + 视图），以幂等迁移 `migrate_v3_1_aligned.sql` 承载，并定义 canonical 存储与写入双写规则。

### Modified Capabilities
<!-- 三端点字段来源由 mock→db，属行为级变化，需 MODIFIED 增量 -->
- `sleep-monitoring-api`: 个性化建议/食物清单来源 mock→配置/计划；录入落 `sleep_log`（+回灌 watch_data）。
- `exercise-analysis-api`: 运动记录时间段/距离 mock→真实列；建议→`user_plans`、成就→聚合查询。
- `nutrition-management-api`: 分餐单品 mock→`recognized_foods`/`meal_breakdown`；运动建议 mock→`user_plans.training_plan`。

## Impact

- **数据库**：新增 `backend/sql/migrate_v3_1_aligned.sql`（v3.1 全量 + 3 补丁 + 缺口列），幂等可重跑；现有库执行=纯加列。
- **代码**：`backend/agents/health_data.py`（换源）、`backend/agents/intake.py`（录入写结构化列+镜像、`/sleep/entry` 写 `sleep_log`）、`backend/scripts/seed_week_history.py`（重刷）。
- **文档**：`docs/接口契约.md`。
- **前端**：无改动。
- **依赖**：无新增。
