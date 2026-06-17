# 实施任务（Layer 2 · 千问 ASR 后端）

> 前置：`add-voice-input-mock`（Layer 1）已落地（契约/录音链路就绪）。环境 conda HPU-3.12。
> 依据：本变更 design.md（共享契约 + 适配器 + 路径①/②/spike）。

## 0. Spike（落地前必做，确定路径）

- [x] 0.1 用 curl 试现有网关 `POST {OPENAI_BASE_URL}/audio/transcriptions`：带一段浏览器 webm/opus + `model=<千问ASR别名>`，看是否 200 返回 text、是否免转码
- [x] 0.2 若①不通：试路径②`/chat/completions` 多模态 `input_audio`(base64) + qwen-audio 模型
- [x] 0.3 都不通：评估 DashScope 直连（新增 `dashscope` dep + key）；确定是否需 ffmpeg 转码
- [x] 0.4 锁定 `ASR_MODE` / `ASR_MODEL`，记入 design Open Questions 结论

## 1. 配置（config/langgraph_config.py）

- [x] 1.1 增 `ASR_MODE`(默认 transcriptions)、`ASR_MODEL`、`ASR_BASE_URL`/`ASR_API_KEY`(默认复用 OPENAI_*)、`ASR_MAX_SECONDS`(60)、`ASR_MAX_MB`(10)

## 2. 适配器（backend/agents/asr.py）

- [x] 2.1 `transcribe_audio(data: bytes, mime: str, filename: str) -> {text, duration_ms?, model}`
- [x] 2.2 路径① transcriptions：`requests.post({ASR_BASE_URL}/audio/transcriptions, files={file:(filename,data,mime)}, data={model:ASR_MODEL}, headers=Authorization)`，解析 text
- [x] 2.3 路径②（兜底，按 spike 决定是否实现）：chat_audio base64 多模态
- [x] 2.4 （仅 spike 必需时）ffmpeg/pydub 转码 webm/opus→16k mono wav
- [x] 2.5 异常包裹：上游失败 raise 受控异常（路由层转 5xx），不裸抛

## 3. 路由（backend/api_server.py）

- [x] 3.1 `POST /api/asr`（`UploadFile`+`Form`）：读字节 → 大小/时长上限校验(超→422) → `asyncio.to_thread(transcribe_audio)` → 返回 {text,...}
- [x] 3.2 ASR 异常 → `HTTPException(5xx, {error})`；无音频 → 422
- [x] 3.3 `/` root endpoints 列表登记 `/api/asr`

## 4. 前端切换（composables/useVoiceInput.ts）

- [x] 4.1 `transcribe(blob)` 由 mock 改为 `fetch('/api/asr', {method:POST, body: FormData(audio=blob, format=mimeType)})` → 取 `{text}`
- [x] 4.2 失败 → 维持 Layer 1 的错误降级（回 idle + 提示）；契约/交互不变
- [x] 4.3 （可选）保留一个 env/flag 在无后端时回退 mock，便于纯前端演示

## 5. 自测与验收（先重启 api_server）

- [x] 5.1 两个聊天框：录音→停止→真实识别文本回填（与 mock 体验一致，仅文本变真）
- [x] 5.2 `curl -F audio=@sample.webm -F format=audio/webm /api/asr` 返回 {text}
- [x] 5.3 无音频/超大文件 → 4xx；上游故障 → 5xx {error}，服务不崩
- [x] 5.4 回归：/chat、/plan、三页、/report/latest 不受影响
