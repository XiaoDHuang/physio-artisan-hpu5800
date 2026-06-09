# 「暴汗艺术家」健康决策助手 · 前端

Vue3 + TypeScript + Vite 的聊天前端，对接 backend FastAPI 的 `/chat`、`/plan`、`/status`、`/conversations` 接口。
UI 基于 ant-design-x-vue（Ant Design X 的 Vue 版，专为 AI 聊天设计）。

> 📑 **完整接口契约见 [`docs/接口契约.md`](../docs/接口契约.md)** ——
> 请求/响应字段、四种对话意图、报告 `chart_data` 图表数据结构、安全熔断语义，均以该文档为准。
> 渲染分工：**后端只产出结构化数据，图表与语音播报由前端渲染**（前端自绘图 + 浏览器 TTS）。

## 技术栈

- Vue 3.5 + TypeScript + Vite 8
- ant-design-vue 4（基础组件）+ ant-design-x-vue 1（Bubble / Sender / Conversations / Prompts）
- Pinia（会话状态）

## 开发

```bash
npm install
npm run dev      # 默认 http://localhost:8080
```

需要同时启动 backend（默认 `http://127.0.0.1:8000`）。
开发期前端所有请求走 `/api` 前缀，由 Vite 代理转发到 backend（见 `vite.config.ts`），无跨域问题。

## 与 backend 的对接

| 前端调用 | 代理到 backend | 用途 |
|----------|---------------|------|
| `POST /api/chat` | `POST /chat` | 发送消息，**返回结构化 JSON**（意图路由：报告/数据录入/偏题/安全熔断） |
| `POST /api/plan` | `POST /plan` | 一键生成健康报告（异步），返回 `task_id` |
| `GET /api/status/{task_id}` | `GET /status/{task_id}` | 轮询任务状态与报告结果（含 `chart_data`） |
| `GET /api/conversations` | `GET /conversations` | 拉取会话列表（左侧历史栏，按更新倒序） |
| `GET /api/conversations/{id}` | `GET /conversations/{id}` | 拉取某会话历史 |
| `DELETE /api/conversations/{id}` | `DELETE /conversations/{id}` | 清空某会话 |

> ⚠️ `/chat` 已由「SSE 流式纯文本」改为「一次性结构化 JSON」（`ChatResponse`）。前端按 `intent` 分支处理：
> `report` 拿 `task_id` 轮询 `/status`；`data_entry` 看 `missing/saved` 决定追问或提示已记录；
> `blocked` 用醒目告警渲染熔断话术；`other` 正常渲染 `reply`。字段详见接口契约文档。

**报告渲染**：`/status` 完成后从 `result.final_report.chart_data` 取四块数据自绘——
RS 半圆仪表盘、HRV/身体年龄 7 日双曲线（对照灰虚线 vs 实验绿实线）、干预前后雷达、训练/餐盘卡片；
`vocal_narrative` 文本用浏览器 TTS 朗读。

**会话列表说明**：左侧历史列表从服务端 `GET /conversations` 拉取（标题取首条用户消息，按最近更新倒序），支持跨设备/跨浏览器。新会话发首条消息时前端先乐观插入到列表顶部，收到响应后重新拉取列表与服务端对齐。

## 目录结构

```
src/
├── api/
│   ├── chat.ts        # 接口封装：sendChat(SSE) / listConversations / getConversation / deleteConversation
│   └── types.ts       # 接口类型
├── components/
│   ├── ChatSidebar.vue   # 左侧历史会话栏
│   ├── ChatPanel.vue     # 右侧 Agent 聊天面板（含底部输入区）
│   └── MessageList.vue   # 消息气泡列表
├── stores/
│   └── chat.ts        # Pinia 会话状态
├── theme.ts           # 主题色板（绿色健康风）
├── App.vue            # 根布局
└── main.ts
```

## 待办（图标占位）

代码中所有图标暂用占位符号，搜索 `TODO[icon]` 可定位，替换为正式图标即可：
- 品牌 Logo、新建按钮、删除菜单
- 用户/助手头像
- 底部工具栏：添加 / 图片识别 / 视频上传 / 语音
