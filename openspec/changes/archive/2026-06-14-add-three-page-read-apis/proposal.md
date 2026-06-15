## Why

前端四个页面中，「健康报告」已实现并跑通（`/dashboard/{uid}` + `/report/latest/{uid}`），但「运动分析 / 睡眠监测 / 饮食管理」三页仍是占位空白。要实现这三页，必须先有稳定的取数接口。设计图已确认，三页所需数据**大部分能从现有表真实聚合**（`watch_data / exercise_records / nutrition_logs / users` 及其 JSONB 列 + `health_data.py` 工具），少部分字段当前表结构缺失。

本变更是三层实施的**第一层（后端契约 + mock）**：先把三页的只读取数端点设计并实现出来，缺失字段在后端用 mock 兜底并标注来源，使第二层前端可以按稳定契约编码。第三层（表设计 + 重刷历史 + mock 换真实源）**独立另起变更**，待表结构定稿后再做——届时前端因只认契约而零改动。

## What Changes

- 新增三个**只读聚合端点**，镜像现有 `GET /dashboard/{uid}` 风格（纯 DB + mock 聚合、毫秒级、不触发多智能体工作流），全部复用 `backend/agents/health_data.py`：
  - `GET /sleep/{uid}` —— 睡眠监测页：今日睡眠概况/时长/小憩/入睡起床/近 7-14 天趋势/个性化建议。
  - `GET /exercise/{uid}` —— 运动分析页：今日运动总览/今日状态/今日运动记录/本周运动趋势/今日运动建议/成就。
  - `GET /nutrition/{uid}?date=` —— 饮食管理页：顶部 4 卡/能量摄入概览/今日饮食记录(分餐)/运动建议。
- 新增一个**轻量写端点** `POST /sleep/entry` —— 用户手动录入入睡/起床/小憩时间，写入 `watch_data.sleep_data` JSONB（`bedtime` / `wake_time` / `nap_minutes` / `total_hours`），**无需建表/改表**。
- 每个端点响应内**逐字段标注来源** `sources: { 字段: db | mock | derived }`，沿用现有 `data_sources` 约定，便于第三层精确换源、便于 UI 标注"真实/模拟"。
- **缺字段统一在后端 mock 兜底**（不暴露给前端、不污染契约）：每餐结构化食物明细、训练方案组数×次数、运动距离/时间段、跨用户成就百分位、睡眠/饮食/运动个性化建议文本。
- 同步更新 `docs/接口契约.md`：新增三页端点与字段表，标明每字段 db/mock/derived 与缺口说明。

> 非目标（明确不做）：不实现任何前端（第二层另起变更）；不做表结构设计/迁移/重刷历史（第三层另起变更）；不接入真实视觉/LLM 生成（沿用现有 mock/规则）；`/chat` 多模态录入沿用现状，本期仅复用、不改。

## Capabilities

### New Capabilities
- `sleep-monitoring-api`: 睡眠监测页只读聚合端点 `GET /sleep/{uid}` 及手动录入端点 `POST /sleep/entry`（写 `sleep_data` JSONB），含趋势区间参数与字段来源标注。
- `exercise-analysis-api`: 运动分析页只读聚合端点 `GET /exercise/{uid}`，聚合今日总览/状态/运动记录/本周趋势/建议/成就，含字段来源标注。
- `nutrition-management-api`: 饮食管理页只读聚合端点 `GET /nutrition/{uid}?date=`，聚合每日目标 KPI/能量概览/分餐记录/运动建议，含字段来源标注。

### Modified Capabilities
<!-- 无：openspec/specs/ 当前为空；现有 /dashboard 等端点未建 spec，本变更不修改其需求。 -->

## Impact

- **代码**：
  - `backend/api_server.py` —— 新增 3 个 GET + 1 个 POST 端点（薄路由，转调聚合层）。
  - `backend/agents/health_data.py` —— 新增三页聚合函数（如 `get_sleep_overview` / `get_exercise_overview` / `get_nutrition_overview`）与睡眠录入写入函数，复用既有 `_query_one/_query_all/_avg/compute_metrics` 与 `health_tools`。
- **数据**：仅读现有表；写仅落 `watch_data.sleep_data` JSONB，**无 DDL**。所有缺字段 mock 集中在聚合层、带 `sources` 标注。
- **文档**：`docs/接口契约.md` 增补三页端点契约。
- **依赖/系统**：无新增依赖；不触发 LangGraph 工作流；不影响已上线的 `/dashboard`、`/report/latest`、`/chat`。
- **下游**：第二层前端变更将按本契约取数；第三层表变更将把 mock 字段换为真实源（前端零改动）。
