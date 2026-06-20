## Context

### 现状（as-is）

```
用户：「帮我生成报告」
  │
  ▼ POST /chat (intent=report)
  │ reply = LLM话术 + "\n\n🤖 多智能体会诊已启动（task_id=uuid），稍后用 /status 查看报告。"
  │
  ▼ 前端 chat.send → pollReportTask (2s × 90)
  │   轮询中：lastReply 不变，ChatDock 仅显示首条 reply（像已结束）
  │   completed：lastReply += "\n\n✅ 报告已生成，页面数据已刷新。"
  │   failed：  lastReply += "\n\n❌ 报告生成失败：" + st.message（可能含 Exception 文本）
  │   timeout： lastReply += "\n\n⏳ 报告仍在生成中，请稍后刷新页面查看。"
  │
  ▼ onReportComplete → reportStore.load()
```

| 问题 | 示例 |
|------|------|
| 技术泄漏 | `task_id=af36…`、`/status` |
| 无进度感 | 60s 内 UI 静止 |
| 日期生硬 | `2026-06-15` 而非「6月15日」 |
| 失败吓人 | `系统错误: connection timeout…` |
| 成功无指引 | 未提示「健康建议已更新、向上查看」 |
| 长任务耦合 | 切日期 / 重复 report / 并行录入时轮询与 `lastReply` 冲突 |

### 依赖（已实现）

- `add-chat-report-by-date`：`anchor_date`、`task_id` 轮询、`onReportComplete`
- `add-demo-user-switch`：`userStore.userName`（小明/小强）
- `add-report-dashboard-by-date`：报告页 Header 日期与 Chat 同步

---

## Goals / Non-Goals

**Goals**

1. 用户全程看不到 `task_id`、API 路径、Python 异常原文
2. 轮询期间有**可感知的进度**（文案或 loading 态）
3. 终态文案包含 **锚点日期**（及可选 **用户名**），与看板刷新行为一致
4. 文案集中管理，便于答辩前微调
5. 会话落库的 assistant 内容仍为**首条即时回复**（不含前端轮询追加），避免 DB 与 UI 不一致
6. **报告长任务与单轮 Chat 解耦**：切日、录入、重复触报告时行为可预期（见 D9–D11）

**Non-Goals**

- 不改 `/status` 响应 schema（仍用 `status/progress/message`）
- 不做 SSE/WebSocket 推送
- 不国际化（仅简体中文）
- **后端**报告任务去重 / 幂等（场景 2 由前端拦截，见 D10）
- 取消或中断已启动的 LangGraph 任务

---

## Decisions

### D1：文案分层——谁说什么

| 阶段 | 负责方 | 存储 / 展示 |
|------|--------|-------------|
| T0 即时确认 | 后端 `/chat` `reply` | 写入 `ai_conversations`；同时写入 `lastReply` |
| T1 轮询进度 | 前端 `activeReportTask` | `reportTaskBanner` + `progressLine`（**不**阻塞 `send`） |
| T2 终态 | 前端模板 | toast + banner；**仅当** `lastIntent==='report'` 且无新问答时更新 `lastReply` |

理由：`task_id` 仅前端持有；长任务生命周期独立于单轮 Chat（D9–D11）。

### D2：后端即时 `reply` 模板（report 意图）

替换现有拼接逻辑（`api_server.py` report 分支）：

```python
# 伪代码 — 见 backend/agents/copy/report_replies.py
def immediate_reply(anchor_date: str, routed_reply: str | None) -> str:
    day_label = format_cn_date(anchor_date)  # 今天 | 6月15日
    lead = (routed_reply or f"好的，正在为你生成{day_label}的健康体检报告。").strip()
    tail = (
        "健康顾问团队正在会诊（生理评估 → 运动建议 → 膳食方案），"
        "大约需要 1～2 分钟，请稍候…"
    )
    return f"{lead}\n\n{tail}"
```

约束：

- **禁止** 在 `reply` 中出现 `task_id`、`/status`、UUID
- LLM `routed.reply` 若已含完整语义，仍**追加**统一 tail（保证有等待预期）；若 LLM 回复过长（>120 字）则只用 LLM 文本 + 一句「请稍候…」

### D3：任务 `message` 用户向化

`assessment_tasks` 与 `run_assessment_task` 内 `message` 改为产品文案：

| status | progress | message（示例） |
|--------|----------|-----------------|
| started | 0 | 正在准备你的健康数据… |
| processing | 20 | 生理指标评估中… |
| processing | 50 | 运动与恢复方案生成中… |
| processing | 80 | 膳食建议与报告汇总中… |
| completed | 100 | 报告已生成 |
| failed | 100 | 报告生成遇到问题，请稍后重试 |

失败时：

- **日志**保留完整异常（现有 `api_logger.error`）
- **对外** `message` 固定为上述友好句，不把 `str(e)` 直接给前端

可选：`message` 增加 `user_message` 字段（本设计 **不扩 schema**，前端按 `status+progress` 映射即可）。

### D4：前端轮询 UX——任务解耦 + 双区 UI

**核心结构**（`stores/chat.ts`）：

```ts
interface ActiveReportTask {
  taskId: string
  userId: number
  anchorDate: string   // 触发时锁定，不随 Header 变化
  progressLine: string
  status: 'running' | 'completed' | 'failed' | 'timeout'
}

state: {
  activeReportTask: ActiveReportTask | null
  // 原有 lastReply / lastIntent / sending …
}
```

- `send()` 在 `intent=report` 时 **启动** `startReportPoll(task)` 后 **立即返回**（不 `await` 轮询）
- 同一 `userId` 全局最多 **1 个** `activeReportTask`（演示期单飞）

**ChatDock 双区**：

```
┌─────────────────────────────────────┐
│ reportTaskBanner（有 active 时）     │  ← T1 进度，全局可见（含营养页）
│ 🔄 6月15日报告生成中 · 生理指标评估中… │
├─────────────────────────────────────┤
│ reply-bar（单轮问答）                │  ← lastReply / sending
│ AI  录入成功 / 引导话术 …            │
└─────────────────────────────────────┘
```

**状态机**：

```
sending=true        → reply-bar: 「正在理解你的需求…」
activeReportTask    → banner 显示 progressLine
lastReply           → 当前这一轮短对话（可与 banner 并存）
```

轮询间隔 **2s**；仅 `progressLine` 变化时更新 banner。

进度映射（`frontend/src/copy/reportChat.ts`）：

```ts
export function mapStatusToProgress(status: string, progress: number): string {
  if (status === 'started') return '正在准备你的健康数据…'
  if (status === 'processing' && progress < 40) return '生理指标评估中…'
  if (status === 'processing' && progress < 70) return '运动与恢复方案生成中…'
  if (status === 'processing') return '膳食建议与报告汇总中…'
  return '正在生成报告…'
}
```

### D5：终态模板与刷新策略

入参：`anchorDate`、`userName?`、`viewingDate`（当前 `reportStore.date`）

```ts
formatCnDate(iso) // 2026-06-19 + today → 「今天」；否则「6月15日」

success(anchor, name?) =>
  name
    ? `✅ ${name}，${formatCnDate(anchor)}的健康报告已生成！看板与健康建议已更新，向上滚动即可查看。`
    : `✅ ${formatCnDate(anchor)}的健康报告已生成！看板与健康建议已更新，向上滚动即可查看。`

failure() =>
  `❌ 报告暂时未能完成，请稍后重试。若多次失败，可切换日期或联系管理员。`

timeout(anchor) =>
  `⏳ ${formatCnDate(anchor)}的报告仍在后台生成，你可以继续浏览；完成后切换日期或刷新页面即可看到最新建议。`

duplicateReportBlocked(anchor) =>
  `${formatCnDate(anchor)}的报告正在生成中，请稍候再试。`

dateSwitchInfoToast(anchor) =>
  `${formatCnDate(anchor)}的健康报告已生成，切换至该日期即可查看。`
```

**看板刷新**（替代无脑 `onReportComplete → load()`）：

```ts
function onReportTaskSettled(task: ActiveReportTask) {
  if (reportStore.date === task.anchorDate) {
    reportStore.load(task.anchorDate, task.userId)
    message.success(formatSuccessToast(task))  // 带日期 + 可选用户名
  } else {
    message.info(`${formatCnDate(task.anchorDate)}的健康报告已生成，切换至该日期即可查看。`)
  }
}
```

**Chat `lastReply` 更新规则**：

| 条件 | 行为 |
|------|------|
| 完成时 `lastIntent === 'report'` 且用户未发新消息 | `lastReply` = success 模板（D5 文案） |
| 完成时用户已进行录入/引导（`lastIntent !== 'report'`） | **不**改 `lastReply`；仅 toast + banner 终态 |
| 失败 / 超时 | banner 终态 + toast；`lastReply` 同上规则 |

```ts
success(anchor, name?) => /* 同前 */

failure() => /* 同前 */

timeout(anchor) => /* 同前 */
```

`ChatSendContext` 扩展：

```ts
export interface ChatSendContext {
  userId?: number
  date?: string
  userName?: string
  onReportComplete?: () => void | Promise<void>  // 可选；默认走 store 内 onReportTaskSettled
}
```

### D6：ChatDock UI

```vue
<!-- banner：有 activeReportTask 时显示（报告页 + 营养页共用 store） -->
<div v-if="chat.activeReportTask?.status === 'running'" class="report-task-banner">
  🔄 {{ formatCnDate(chat.activeReportTask.anchorDate) }}报告生成中 · {{ chat.activeReportTask.progressLine }}
</div>

<!-- reply-bar：单轮问答 -->
<span v-if="chat.sending" class="reply-text thinking">正在理解你的需求…</span>
<span v-else class="reply-text">{{ chat.lastReply }}</span>
```

说明：轮询进度 **只走 banner**；`reply-bar` 不再用 `polling` 占位，避免与录入回复抢视觉焦点。

### D7：与 LLM 路由 reply 的关系

意图路由 prompt 仍可生成个性化 `reply`（如「收到，我来帮你分析 6 月 10 日的恢复情况」）。后端 report 分支：

1. 优先采用 LLM `reply` 作为 lead
2. 统一追加等待预期 tail（D2）
3. 不再把 LLM 可能编造的「请打开某某页面」当作唯一信息源

### D8：接口契约与演示

更新 `docs/接口契约.md` 示例：

```json
{
  "intent": "report",
  "task_id": "…",
  "anchor_date": "2026-06-15",
  "reply": "好的，正在为你生成6月15日的健康体检报告。\n\n健康顾问团队正在会诊（生理评估 → 运动建议 → 膳食方案），大约需要 1～2 分钟，请稍候…"
}
```

注明：`task_id` 仅结构化字段，**不应**出现在 `reply` 字符串内。

### D9：场景 1 —— 生成中切换报告页日期（已确认）

**策略**：前端 **丢弃 Chat 会话展示态**，后台任务 **继续跑**。

| 动作 | 行为 |
|------|------|
| 用户 Header `prevDay` / `nextDay` | `reportStore.load(新日期)`；调用 `chat.clearConversationUi()` |
| `clearConversationUi()` | 清空 `lastReply`、`lastQuestion`、`lastIntent`；**保留** `conversationId`、`activeReportTask` |
| 后台 LangGraph | **不取消**，轮询继续 |
| 任务完成 | 见 D5「看板刷新」：`viewingDate === anchorDate` → `load` + success toast；否则 info toast |

**不在切日时做的事**：

- 不重置 `conversationId`（同一会话内先报告再切日，语义连贯）
- 不停止 `/status` 轮询
- 不在切日瞬间调用 `onReportComplete`

**ReportView 接线**：

```ts
watch(() => store.date, (next, prev) => {
  if (prev && next !== prev && chat.activeReportTask?.status === 'running') {
    chat.clearConversationUi()
  }
})
```

可选增强（P2）：Header 日期旁显示「1 个报告生成中」角标。

### D10：场景 2 —— 生成中再次要求生成报告（已确认）

**策略**：**仅前端拦截**；后端 **本期不加固**（仍可能创建多个 task，但前端单飞阻止用户触发）。

拦截点：`chat.send()` 在 `POST /chat` **之前**：

```ts
if (looksLikeReportRequest(msg) && activeReportTask?.status === 'running') {
  lastReply = duplicateReportBlocked(activeReportTask.anchorDate)
  // 例：「6月15日的报告正在生成中，请稍候再试。」
  return
}
```

| 入口 | 处理 |
|------|------|
| 用户输入含 report 意图 | 本地拦截 + 友好 `lastReply` |
| 建议气泡「帮我生成…报告」 | `:disabled="!!activeReportTask"` 或点击走同上拦截 |

**单飞范围**：同一 `userId` 全局 1 个 `activeReportTask`（含不同锚点日——演示期简单起见一并拒绝并提示「请等待当前报告完成」）。

后端 Out of Scope：同 `(user_id, anchor_date)` 返回已有 `task_id` 的幂等 API。

### D11：场景 3 —— 生成中进行别的对话（已确认）

**策略**：报告 **后台跑**；Chat **允许非 report**；完成 **toast + banner**，不污染录入回复。

| 意图 | 进行中是否允许 |
|------|----------------|
| `data_entry` | ✅ |
| `other` | ✅ |
| `blocked` | ✅ |
| `report` | ❌（D10） |

**时序示例**：

```
T0  「生成报告」→ activeReportTask 启动，lastReply=T0 确认句，banner 显示进度
T1  「录入跑步 5km」→ 正常 POST /chat，lastReply 覆盖为录入结果；banner 仍在
T2  报告完成 → toast；若 viewingDate===anchor 则 load()；lastReply 保持录入结果
```

**实现要点**：

- `send()` 不再 `await pollReportTask`；录入与 report 轮询并行
- 完成回调 **禁止** 无条件 `lastReply += '✅ 报告已生成'`
- `NutritionChatDock` 共用 store：banner 全局可见，避免切页后「隐形任务」

---

## 数据流（to-be）

```mermaid
sequenceDiagram
    participant U as 用户
    participant UI as ChatDock
    participant CS as chat store
    participant RS as report store
    participant API as POST /chat
    participant ST as GET /status

    U->>UI: 生成报告(D1)
    UI->>CS: send(msg, {date:D1})
    CS->>API: message + user_id + date
    API-->>CS: reply, task_id, anchor_date
    CS->>CS: lastReply=reply; startReportPoll
    loop 非阻塞 每2s
        CS->>ST: getTaskStatus
        ST-->>CS: status, progress
        CS->>UI: banner 更新 progressLine
    end
    U->>RS: Header 切到 D2
    RS->>RS: load(D2)
    CS->>CS: clearConversationUi (保留 activeReportTask)
    Note over CS: 轮询继续
    CS->>CS: task completed
    alt viewingDate === D1
        CS->>RS: load(D1)
        CS->>UI: success toast
    else viewingDate === D2
        CS->>UI: info toast「切换至 D1 查看」
    end
```

**并行录入**（场景 3）：T0 启动 poll 后，用户 `send(录入)` 仍走 `/chat`，banner 与 `lastReply` 独立更新。

---

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 轮询原地改文案导致「闪一下」 | 仅 progress 变化时更新；CSS `thinking` 动画 |
| 营养页等同组件误显示 polling | 仅 `intent===report'` 进入 poll；其他 intent `polling` 恒 false |
| 用户刷新页面丢失终态文案 | 可接受（单轮会话设计）；看板数据仍在 |
| LLM lead + 固定 tail 略啰嗦 | tail 一句化；LLM 过长时缩短 tail |
| 中文日期与 anchor 跨月演示 | 统一 `formatCnDate`，单测 2～3 个 ISO 样例 |
| 切日后用户不知后台仍在跑 | `reportTaskBanner` 持续显示锚点日与进度 |
| 前端单飞但后端仍可多 task | 演示可接受；答辩说明「UI 单飞，后端未去重」 |
| 录入完成瞬间 report 完成 | toast 与 lastReply 分离，不 append 到录入回复 |
| 刷新页面丢失 activeReportTask | 可接受；用户可对该日重新触报告 |

---

## Migration Plan

1. **后端**：copy 模块 + report 分支 reply + task message 脱敏
2. **前端核心**：`activeReportTask` + 非阻塞 `startReportPoll` + `clearConversationUi` + D5 刷新策略
3. **前端 UI**：`reportChat.ts` copy；`ChatDock` banner；`ReportView` watch 日期；营养页 banner
4. **场景 2**：`send()` 前端 report 拦截 + 建议气泡 disabled
5. **文档**：`docs/接口契约.md`
6. **回归**：场景 1 切日 + 场景 2 重复 report + 场景 3 录入并行 + 基础话术

无 API breaking change。

---

## Open Questions（已确认 / 默认）

| # | 问题 | 结论 |
|---|------|------|
| 1 | 轮询 UI 用单行 progress 还是首段+子行？ | **banner 单行 progress** |
| 2 | 成功话术是否带用户名？ | **带** |
| 3 | 历史日再次生成是否提示覆盖计划？ | **本期不加** |
| 4 | 切日期时会话如何处理？ | **清空 Chat 展示态，任务继续**（D9） |
| 5 | 重复 report 谁拦？ | **仅前端**（D10） |
| 6 | 生成中能否录入？ | **可以**；完成 toast 不盖录入 reply（D11） |
