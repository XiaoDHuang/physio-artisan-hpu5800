## 1. 后端话术

- [x] 1.1 新建 `backend/agents/copy/report_replies.py`：`format_cn_date`、`immediate_reply`
- [x] 1.2 `api_server.py` report 分支改用 `immediate_reply`，移除 `task_id`/`/status` 拼接
- [x] 1.3 `assessment_tasks` / `run_assessment_task` 的 `message` 改为用户向进度句；`failed` 对外脱敏

## 2. 前端任务解耦与文案

- [x] 2.1 新建 `frontend/src/copy/reportChat.ts`：日期格式化、进度映射、终态/拦截/切日 toast 模板
- [x] 2.2 `chat` store：`activeReportTask`、`startReportPoll`（非阻塞）、`clearConversationUi`
- [x] 2.3 `onReportTaskSettled`：看板日期 === 锚点日才 `load()`，否则 `message.info`
- [x] 2.4 完成/失败/超时：仅当 `lastIntent==='report'` 时更新 `lastReply`；否则 toast + banner
- [x] 2.5 `ChatSendContext.userName`；移除 `send()` 内 `await pollReportTask`

## 3. UI

- [x] 3.1 `ChatDock.vue` + `ReportTaskBanner.vue`：running / 终态 3s
- [x] 3.2 `ReportView.vue`：传 `userName`；`watch(date)` 在任务 running 时 `clearConversationUi`
- [x] 3.3 `NutritionChatDock.vue`：展示同一 `reportTaskBanner`

## 4. 并发边界（D9–D11）

- [x] 4.1 **场景 1**：切日清 `lastReply` 等，保留 `activeReportTask` + `conversationId`
- [x] 4.2 **场景 2**：`activeReportTask` 存在时前端拦截 report（不调 `/chat`）；建议气泡 disabled
- [x] 4.3 **场景 3**：录入/other/blocked 正常 `send`；与 banner 并行不互斥

## 5. 文档与验证

- [x] 5.1 更新 `docs/接口契约.md` report 示例 reply
- [x] 5.2 回归：基础话术 + 场景 1 切日 + 场景 2 重复 report + 场景 3 录入并行（需本地手动点测）
