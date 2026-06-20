## Why

健康报告页已支持按 `date` 锚点查看历史看板（`GET /dashboard/{uid}?date=`），但 **Chat 触发报告生成仍固定用「最新一天 + 默认用户 1」**：

- `POST /chat` 的 `ChatRequest` 无 `user_id` / `date`，报告分支写死 `intake.DEFAULT_USER_ID`
- 编排层 `get_health_snapshot()` 始终 `ORDER BY date DESC LIMIT 1`，与用户在 Header 选中的日期无关
- `build_report_payload()` 调用 `get_week_overview(user_id)` 未传锚点日期
- `user_plans` 回写固定 `plan_date = today()`，历史日触发的报告会污染「今日计划」
- 前端 `postChat` 未传当前演示用户与报告页日期

用户在报告页切到 6 月 15 日并说「生成报告」时，期望基于 **该日数据** 会诊，并与看板 KPI 一致。

## What Changes

- **扩展** `POST /chat`、`POST /plan` 请求体：`user_id`（演示用户）、`date`（报告锚点日 `YYYY-MM-DD`，默认今天）
- **扩展** 意图路由：从用户话术抽取 `on_date`（如「帮我生成 6 月 15 日的报告」），与显式参数合并（显式优先）
- **贯通** 报告任务链路：`on_date` → `run_health_assessment` → `get_health_snapshot(on_date)` → `build_report_payload(on_date)` → `save_user_plan(plan_date=on_date)`
- **扩展** `GET /report/latest/{user_id}?date=`（可选）：按锚点日读取已缓存报告；无则 404
- **扩展** 前端：报告页 `ChatDock` 发送 chat 时附带 `user_id` + 当前 `reportStore.date`；轮询完成后仅当 `anchor_date` 与看板日期一致时展示健康建议三卡
- **同步** `docs/接口契约.md`

## Capabilities

### New Capabilities

- `chat-report-by-date`：`/chat` 与 `/plan` 按用户 + 锚点日期触发多智能体报告，数据层与 dashboard 日期语义对齐

### Modified Capabilities

- `agent-plan-writeback`：`plan_date` 改为报告锚点日（非固定 today）
- `nutrition-management-ui`（轻量）：报告页 ChatDock 传参约定（复用组件，行为在 report 页上下文生效）

## Impact

| 层级 | 文件 / 模块 |
|------|-------------|
| API | `backend/api_server.py` — ChatRequest/PlanRequest/路由/任务元数据 |
| 数据 | `backend/agents/health_data.py` — `get_health_snapshot`、`_compute_baselines` 按锚点日取数 |
| 编排 | `backend/agents/langgraph_agents.py` — state 增加 `on_date` |
| 报告 | `backend/agents/report_payload.py` — `get_week_overview(user_id, on_date=…)` |
| 存储 | `backend/store/postgres_store.py` — 报告缓存带 `anchor_date`；`load_latest` 支持按日筛选 |
| 前端 API | `frontend/src/api/chat.ts`、`types.ts` |
| 前端状态 | `frontend/src/stores/chat.ts`、`stores/report.ts` |
| 文档 | `docs/接口契约.md` |

## Out of Scope（本期不做）

- 按日期批量预生成报告 / 报告日历 UI
- 改变 `control` / `experiment` 双场景 mock 协议（保留兼容，与 seed v31 真实日期数据并存）
- 饮食/运动/睡眠页 ChatDock 的历史日报告（首期仅报告页传 `date`）
