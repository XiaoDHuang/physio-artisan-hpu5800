# 暴汗艺术家 · HPU 健身训练助手

Health Personal Unit — 健身 × 饮食 × 睡眠综合管理系统。

## 架构

```
frontend/   Vue 3 + TypeScript + Vite（聊天 UI、睡眠/运动/营养页、健康报告）
backend/    FastAPI + LangGraph 多智能体（/chat、/plan、聚合读 API、ASR/TTS）
openspec/   规范驱动变更（proposal → design → tasks → 实施）
docs/       接口契约、答辩文档
.agents/    跨工具共享的 commands / skills（Claude、Cursor、Codex 软链到此）
```

## 技术栈

- **前端**：Vue 3.5、Pinia、ant-design-x-vue；开发端口默认 8080，代理 `/api` → backend
- **后端**：FastAPI、LangGraph、LangChain；默认 `http://127.0.0.1:8000`
- **AI**：OpenAI 兼容接口（DeepSeek 等）；Langfuse 可观测性
- **Python**：3.12+，团队本地 conda 环境 `HPU-3.12`

## 常用命令

```powershell
# 后端（在 backend/ 目录）
& "D:\Program Files\miniconda3\envs\HPU-3.12\python.exe" api_server.py

# 前端（在 frontend/ 目录）
npm install && npm run dev
```

GBK 控制台跑 Python 若遇 emoji 编码错误，可设 `$env:PYTHONUTF8="1"`。

## 开发约定

- 接口变更同步更新 `docs/接口契约.md`
- 新功能优先走 OpenSpec：`.agents/commands/opsx/` 与 `.agents/skills/openspec-*`
- 后端业务逻辑在 `backend/agents/`、`backend/store/`；前端 API 封装在 `frontend/src/api/`
- 只改任务相关代码，避免无关重构；不提交 `.env`、日志、本地备忘

## 目录要点

| 路径 | 说明 |
|------|------|
| `backend/api_server.py` | FastAPI 入口 |
| `backend/agents/langgraph_agents.py` | 多智能体编排 |
| `backend/agents/health_data.py` | 三页聚合读 API 数据层 |
| `frontend/src/views/` | 睡眠 / 运动 / 营养 / 报告页面 |
| `openspec/specs/` | 已归档的正式规范 |
| `openspec/changes/` | 进行中的变更 |

## 跨工具 AI 配置

共享内容在 `.agents/`。克隆后若 `.claude/commands` 等不存在，运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-agent-links.ps1
```

个人本地备忘可写在 `AGENTS.local.md`（已 gitignore），Claude 用户亦可用 `CLAUDE.local.md`。
