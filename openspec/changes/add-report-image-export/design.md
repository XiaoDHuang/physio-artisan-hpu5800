## Context

当前 /report 页面已有完整的数据可视化看板（KpiCards + BodyOverview + ECharts 图表 + 健康建议 + ChatDock），且已完成 TTS 语音合成（Text→Speech）。用户看到的报告页面实际上是 Vue 组件渲染的 DOM，无法直接保存为图片。目标是在现有的 ASR / TTS 多模态能力上补齐 Image 生成，形成多模态三角。

`AppHeader.vue` 中已有"导出报告"按钮但无点击逻辑。所有数据存在于 Pinia `useReportStore` 中。

后端已有的 TTS 适配器模式（`backend/agents/tts.py` + `POST /tts`）将作为 Image 适配器的参考模板。

## Goals / Non-Goals

**Goals:**
- 点击"导出报告"按钮 → 收集当前页面报告数据 → 后端调用大模型生成可视化的报告图片 → 前端展示并自动下载
- 后端两条路径：① Chat Completions + `modalities: ["image"]`（主路径）、② `POST /images/generations`（兜底）
- 图片生成 prompt 由后端根据报告数据结构动态构造，不需要前端手写 prompt
- 生成的图片为 PNG 格式，在浏览器展示 + 触发 download

**Non-Goals:**
- 不作为独立的 REST API 对外暴露（仅内部 /report 页面使用）
- 不存储历史图片（每次点击实时生成）
- 不改变现有报告页面的 DOM/样式
- 不处理报告图片生成失败后的灰度降级（直接报错提示）

## Decisions

**D1: Chat Completions + `modalities: ["image"]` 作为主路径，对称于 TTS 的 `modalities: ["audio"]`**

TTS 主路径是 `/audio/speech`，兜底是 `modalities: ["audio"]`。Image 反其道：主路径用 `modalities: ["image"]`（与 ASR 同模式的多模态 Chat），兜底用 `/images/generations`（OpenAI 标准图片生成端点）。

原因：多模态 Chat 路径允许我们在 messages 中附带结构化的报告数据作为 system prompt，让模型理解上下文后生成更准确的报告图片；`/images/generations` 只接受一句 prompt，对精确数据布局的控制力更弱。

**D2: 后端构造 prompt，前端只传数据**

前端 `useReportExport` 从 Pinia store 收集结构化数据（JSON），通过 `POST /api/report-image` 发给后端。后端 `image_gen.py` 根据模板将数据渲染为一段详细的中文 prompt（含数值、布局指令、设计风格），然后发给大模型生成图片。

前端不写 prompt，保持在纯 UI 层。复杂逻辑在后端。

**D3: 图片返回 URL（Base64 Data URL），前端用 `<img>` 展示 + 自动下载**

后端返回 `image/png` 二进制 → 前端 `URL.createObjectURL(blob)` → `<img>` 展示。同时创建一个隐藏的 `<a download>` 触发浏览器下载。这与 TTS 的 Audio blob 模式一致。

**D4: 下载完成后展示预览 modal，而非直接替换页面**

生成图片后弹出一个预览弹窗，显示报告图片 + [下载] [关闭] 两个按钮。用户可查看图片效果后再决定是否保存。

**D5: Image 代理地址复用现有网关**

对称于 TTS，`IMAGE_BASE_URL` 默认复用 `OPENAI_BASE_URL`，`IMAGE_API_KEY` 默认复用 `OPENAI_API_KEY`。

## Risks / Trade-offs

- [R] 网关可能不支持 `modalities: ["image"]` → 已设计了 `/images/generations` 兜底
- [R] 大模型生成的数据数字可能不精确 → prompt 中明确要求模型不要虚构数据，使用提供的具体数值
- [R] 图片生成耗时可能较长（10-30s） → 前端按钮加 loading 状态，显示"正在生成报告图片..."
- [R] 中文渲染在大模型图片生成中可能乱码 → prompt 中用中文 + 英文关键词双语描述，并在 prompt 中要求用清晰中文标注
