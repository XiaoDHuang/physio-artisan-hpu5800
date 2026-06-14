## Why

变更①②已上线：三页只读端点 + 四页前端，缺失字段在后端以 mock 兜底并带 `sources` 标记。第三层的目标是**扩展数据表结构、把这些 mock 字段替换为真实数据**，使 `sources` 从 `mock` 变为 `db`，且前端因只认契约而零改动。

换源清单见 `openspec/changes/archive/2026-06-14-add-three-page-read-apis/design.md` 的"实现纪要"。

## What Changes

- **新增 `meal_items` 表**（分餐单品明细）：解决饮食页 `meals[].foods[]`（name/grams/calories/餐别/时间）结构缺口，同时供报告页"明日三餐"。与 `/chat` 多模态录入（饮食拍照）写入路径打通。
- **`exercise_records` 扩列**：`start_time` / `end_time`（运动时间段）、`distance_km`（距离）—— 解决运动记录 mock 字段。
- **睡眠录入正式化**：`bedtime` / `wake_time` / `nap_minutes` 目前存 `watch_data.sleep_data` JSONB（已半真实）；本层确认是否升列或保留 JSONB（见 design 决策）。
- **建议/方案/成就真实化**：睡眠/运动个性化建议文本、饮食页训练方案（组数×次数）改由 agent/LLM 产出或建议表；运动成就 `percentile` 改为跨用户人群聚合查询。
- **推荐/避免食物**：改为对齐前端图标集的 curated 配置（香蕉/燕麦/鸡蛋/牛奶/坚果·咖啡/辛辣食物/油炸食品/甜点/奶茶）。
- **聚合层换源**：`health_data.py` 三个 `*_overview` 的 mock 分支替换为真实查询，`sources` 标 `db`/`derived`。
- **重刷历史数据**：更新 `seed_week_history.py`（goals 对齐 10000/60/2000/500、填充新列与 `meal_items`），并修正"仅录睡眠行遮蔽运动总览"的数据问题。
- **同步契约**：`docs/接口契约.md` 各 mock 字段标注更新为真实来源。

> 非目标：不改前端（契约字段不变）；不改四页 UI/交互；端点路径与响应结构保持稳定（仅字段来源由 mock→db）。

## Capabilities

### New Capabilities
- `health-db-schema`: 第三层数据表结构扩展（`meal_items` 表、`exercise_records` 扩列、睡眠录入字段、goals 缺省），以幂等迁移 + 重刷脚本承载。

### Modified Capabilities
<!-- 这三个端点的"字段来源/兜底行为"由 mock 改为真实 DB，属需求级行为变化，需 MODIFIED 增量 spec -->
- `sleep-monitoring-api`: 个性化建议/食物清单、录入字段来源由 mock 改为真实/配置。
- `exercise-analysis-api`: 运动记录时间段/距离、建议、成就由 mock 改为真实 DB/聚合。
- `nutrition-management-api`: 分餐单品明细、训练方案由 mock 改为真实 `meal_items`/agent。

## Impact

- **数据库**：`meal_items` 新表 + `exercise_records` 扩列（幂等 DDL 迁移 `backend/sql/migrate_layer3.sql`）。
- **代码**：`backend/agents/health_data.py`（换源）、`backend/scripts/seed_week_history.py`（重刷）、可能 `backend/agents/intake.py`（多模态/录入写 `meal_items`）、agents（建议/训练方案）。
- **文档**：`docs/接口契约.md`。
- **前端**：无改动（契约稳定）；mock 角标若实现可自动转真实标识。
- **依赖**：无新增。
