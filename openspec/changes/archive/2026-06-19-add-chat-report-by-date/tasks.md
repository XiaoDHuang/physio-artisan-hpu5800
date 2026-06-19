## 1. 数据接入层（backend/agents）

- [x] 1.1 `get_health_snapshot(user_id, mode, on_date)`：watch/exercise/nutrition 按锚点日查询；`_compute_baselines` 仅用 `date < on_date`
- [x] 1.2 `build_report_payload(user_id, result, on_date)`：调用 `get_week_overview(user_id, on_date=on_date)`
- [x] 1.3 `langgraph_agents`：state / `run_health_assessment` 传递 `on_date` 至 DataLoader

## 2. API 与任务链路（backend/api_server.py）

- [x] 2.1 `ChatRequest` 增加 `user_id`、`date`；`ChatResponse` 增加 `anchor_date`
- [x] 2.2 `PlanRequest` 增加 `date`；创建任务时写入 `anchor_date`
- [x] 2.3 报告分支使用 `request.user_id`；`run_assessment_task` → `save_user_plan(plan_date=on_date)`
- [x] 2.4 意图路由 prompt 增加 `on_date` 抽取；实现日期合并与校验（未来日 422）
- [x] 2.5 数据录入 / 安全日志同步 `request.user_id`

## 3. 报告缓存（backend/store）

- [x] 3.1 `save_assessment_artifacts`：在 `recommendations` 写入 `anchor_date`
- [x] 3.2 `load_latest_assessment(user_id, on_date=None)`：支持按 `anchor_date` 筛选
- [x] 3.3 `GET /report/latest/{user_id}?date=` 端点扩展

## 4. 前端

- [x] 4.1 `api/chat.ts` + `types`：`PostChatParams` 增加 `user_id?`、`date?`
- [x] 4.2 `stores/chat.ts`：`send` 接受上下文参数；报告意图时保存 `task_id` / `anchor_date`
- [x] 4.3 报告页 `ChatDock`（或 composable）：传 `userStore.userId` + `reportStore.date`
- [x] 4.4 `stores/report.ts`：`healthAdvice` 按 `anchor_date === date` 门控；`getLatestReport(uid, date)`
- [x] 4.5 可选：`/status` 轮询 + 完成后 `reportStore.load()`

## 5. 文档与验证

- [x] 5.1 更新 `docs/接口契约.md`（/chat、/plan、/report/latest）
- [x] 5.2 手工验证：选 seed 14 天内某日 → dashboard 与 chat 触发后 chart_data.dashboard 一致
- [x] 5.3 切换 user1/user2 + 日期，确认 user_id 贯通
