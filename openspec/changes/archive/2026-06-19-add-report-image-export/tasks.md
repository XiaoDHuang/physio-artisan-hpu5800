## 1. 后端配置

- [ ] 1.1 在 `langgraph_config.py` 新增 `IMAGE_MODEL` / `IMAGE_BASE_URL` / `IMAGE_API_KEY` 配置项，默认复用 OPENAI 网关

## 2. 后端图片生成适配器

- [ ] 2.1 新建 `backend/agents/image_gen.py`，实现 `generate_report_image(data: dict) -> bytes`
- [ ] 2.2 路径①：`_generate_via_chat_image(data, prompt)` — Chat Completions + `modalities: ["image"]`，构造系统 prompt + 报告数据
- [ ] 2.3 路径②：`_generate_via_image_gen(prompt)` — `POST /images/generations` 标准端点兜底
- [ ] 2.4 带 429 重试逻辑（复用 tts.py 的 `_post_with_retry` 模式或提取公共）
- [ ] 2.5 `build_report_prompt(data)` — 根据报告 JSON 数据构造中文图片生成 prompt（含布局指令、设计风格、数据完整性约束）

## 3. 后端路由

- [ ] 3.1 在 `api_server.py` 新增 `POST /api/report-image` 端点
- [ ] 3.2 请求体 `ReportImageRequest`：接收报告数据 JSON（kpi / body / sleep / nutrition / exercise / healthAdvice）
- [ ] 3.3 返回 `Response(content=png_bytes, media_type="image/png")`
- [ ] 3.4 异常处理：校验失败 → 422，生成失败/超时 → 502

## 4. 前端数据提取

- [ ] 4.1 新建 `frontend/src/composables/useReportExport.ts`
- [ ] 4.2 `buildReportData()` — 从 `useReportStore` 收集 KPI / 身体 / 睡眠 / 饮食 / 运动 / 健康建议全部数据，构造发送给后端的 JSON
- [ ] 4.3 `exportReportImage()` — 调用 `fetch('/api/report-image')` → Blob → 返回 ObjectURL

## 5. 前端 UI 接入

- [ ] 5.1 在 `AppHeader.vue` "导出报告"按钮绑定 click 事件，调用 `useReportExport`
- [ ] 5.2 按钮增加 loading 状态，显示"正在生成报告图片..."
- [ ] 5.3 新建报告图片预览弹窗组件（或内联在 AppHeader/ReportView 中）
- [ ] 5.4 弹窗包含：生成的图片 + [下载] [关闭] 按钮
- [ ] 5.5 自动触发浏览器下载（`<a download>` + click）

## 6. 自测验证

- [ ] 6.1 打开 /report 页面 → 点击"导出报告" → 按钮 loading → 弹窗展示报告图片 → 浏览器自动下载 png
- [ ] 6.2 后端离线时 → 点击导出 → 显示错误提示
- [ ] 6.3 vue-tsc + vite build 通过
