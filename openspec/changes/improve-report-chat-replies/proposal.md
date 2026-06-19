## Why

`add-chat-report-by-date` 已打通「报告页选日 → Chat 触发 → 轮询 `/status` → 刷新看板」链路，但面向用户的 **机器人话术仍偏开发态**：

- 后端 `intent=report` 的 `reply` 拼接 `task_id`、`/status` 等内部信息
- 轮询期间 ChatDock 无进度反馈，用户只能盯着首条回复等待 1～2 分钟
- 完成/失败/超时文案笼统，未呼应 **锚点日期**、**演示用户名**，失败时可能直接暴露 `系统错误: …` 堆栈式文本
- `docs/接口契约.md` 示例仍含 `task_id=…`，与产品演示口径不一致
- **长任务与单轮 Chat 未解耦**：切日期、重复触报告、并行录入时，轮询与 `lastReply` 互相覆盖，完成回调可能刷新错误日期

答辩/demo 场景需要：**像健康助手在对话，而不是像 API 文档**；报告生成在后台可靠完成，不干扰用户继续浏览或录入。

## What Changes

- **优化** 后端报告意图即时 `reply`：去掉技术字段，改为自然中文 + 锚点日友好表述 + 预计耗时
- **优化** 后台任务 `assessment_tasks[].message`：全部改为可安全展示给用户的进度话术（供前端映射或直接展示）
- **优化** 前端 `chat` store 轮询逻辑：轮询中更新进度文案；完成/失败/超时使用带日期（及可选用户名）的模板
- **增强** `ChatDock`：轮询阶段显示「生成中」态（与 `sending` 区分），避免界面像「已经答完」
- **新增** 轻量文案常量模块（前后端各一处），避免散落硬编码
- **同步** `docs/接口契约.md` 中 report 分支 reply 示例
- **解耦** 报告长任务与单轮 Chat：`activeReportTask` 独立轮询（非阻塞 `send`），`reportTaskBanner` 展示进度
- **场景 1（切日期）**：Header 换日时 **清空 Chat 会话展示态**（`lastReply` 等），后台任务 **继续跑**；完成时仅当看板日期 = 锚点日才 `load()`，否则 toast 提示切换日期查看
- **场景 2（重复报告）**：**仅前端拦截**——有进行中的 `activeReportTask` 时拒绝再次触发 report（不调 `/chat`）；后端任务幂等 **本期不做**
- **场景 3（并行对话）**：生成报告中仍允许 `data_entry` / `other` / `blocked`；完成用 toast + banner，**不**向非 report 的 `lastReply` 追加成功句

## Capabilities

### New Capabilities

- `report-chat-replies`：报告生成全链路（即时回复 + 轮询进度 + 终态反馈）的用户向话术规范与实现

### Modified Capabilities

- `chat-report-by-date`：在已有 `anchor_date` / 轮询行为上，补充话术与 UI 进度约定（行为不变，体验增强）
- `nutrition-management-ui`（轻量）：共享 `ChatDock` / `chat` store 的轮询 UI 态（非 report 意图不受影响）

## Impact

| 层级 | 文件 / 模块 |
|------|-------------|
| API | `backend/api_server.py` — report 分支 `reply`、任务 `message`、失败 message 脱敏 |
| 文案 | `backend/agents/copy/report_replies.py`（新建，可选集中模板） |
| 前端状态 | `frontend/src/stores/chat.ts` — `activeReportTask`、非阻塞轮询、切日清会话、report 拦截 |
| 前端 UI | `ChatDock.vue` — `polling` + `reportTaskBanner`；`ReportView.vue` — 监听日期切换 |
| 前端文案 | `frontend/src/copy/reportChat.ts`（新建） |
| 文档 | `docs/接口契约.md` |

## Out of Scope（本期不做）

- 改造 `data_entry` / `other` / `blocked` 话术（除顺带去掉 report 误拼接）
- 多轮聊天气泡 / 历史消息列表（仍保持单轮覆盖式 `lastReply`）
- 后端在轮询完成后回写会话历史中的「终态 reply」（终态文案仅前端内存展示）
- `/plan` 一键按钮的 toast/弹窗文案（可后续复用同一 copy 模块）
- 后端同 `(user_id, anchor_date)` 报告任务幂等 / 去重（场景 2 仅前端拦截）
- 同一用户多日期并行多个报告任务（演示期单飞：全局最多 1 个 `activeReportTask`）
