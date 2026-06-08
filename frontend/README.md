# 健身训练助手 · 前端

Vue3 + TypeScript + Vite 的机器人聊天前端，对接 backend FastAPI 的 `/chat`、`/conversations` 接口。
UI 基于 ant-design-x-vue（Ant Design X 的 Vue 版，专为 AI 聊天设计）。

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
| `POST /api/chat` | `POST /chat` | 发送消息，SSE 流式接收 |
| `GET /api/conversations` | `GET /conversations` | 拉取会话列表（左侧历史栏，按更新倒序） |
| `GET /api/conversations/{id}` | `GET /conversations/{id}` | 拉取某会话历史 |
| `DELETE /api/conversations/{id}` | `DELETE /conversations/{id}` | 清空某会话 |

**会话列表说明**：左侧历史列表从服务端 `GET /conversations` 拉取（标题取首条用户消息，按最近更新倒序），支持跨设备/跨浏览器。新会话发首条消息时前端先乐观插入到列表顶部，流式结束后重新拉取列表与服务端对齐。

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
