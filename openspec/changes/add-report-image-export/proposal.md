## Why

当前 /report 页面的"导出报告"按钮无任何功能，用户无法将报告页面内容保存为图片。同时，该项目已完成 TTS（文本→语音）多模态能力，顺势补齐"数据→图片"能力，形成完整的 ASR / TTS / Image 多模态三角，满足多模态生成作业要求。

## What Changes

- **新建** 后端图片生成适配器 `backend/agents/image_gen.py`，封装大模型图片生成调用（Chat Completions + `modalities: ["image"]` 主路径，`/images/generations` 兜底）
- **新建** 后端路由 `POST /api/report-image`，接收报告数据 JSON，返回 png 图片二进制流
- **配置** `langgraph_config.py` 新增 `IMAGE_MODEL` / `IMAGE_BASE_URL` / `IMAGE_API_KEY` 配置项
- **接入** `AppHeader.vue` 中"导出报告"按钮，点击后收集页面数据 → fetch 后端生成图片 → 前端展示 + 触发浏览器下载
- **提取** 报告数据结构提取逻辑到 `frontend/src/composables/useReportExport.ts`，负责从 Pinia store 整理生成图片所需的 JSON 数据

## Capabilities

### New Capabilities

- `report-image-export`: 用户点击"导出报告"按钮，系统将当前报告页数据发给大模型生成可视化报告图片，并在前端展示和下载

### Modified Capabilities

（无现有 capability 受影响）

## Impact

| 文件 | 操作 |
|------|------|
| `backend/config/langgraph_config.py` | 新增 IMAGE_MODEL / IMAGE_BASE_URL / IMAGE_API_KEY 配置 |
| `backend/agents/image_gen.py` | 新建：`generate_report_image(data) -> bytes` |
| `backend/api_server.py` | 新增 `POST /api/report-image` 端点 |
| `frontend/src/composables/useReportExport.ts` | 新建：从 store 提取报告数据结构 |
| `frontend/src/components/common/AppHeader.vue` | "导出报告"按钮接入导出逻辑 |
