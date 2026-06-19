## Context

`add-voice-input-mock`（Layer 1）已定契约与录音链路：前端 `useVoiceInput` 真录音产出 Blob，`transcribe(blob)` 为唯一替换点。本变更（Layer 2）实现 `POST /api/asr` 把 Blob 转文字。

现有基础：`OPENAI_BASE_URL`(apiyi 网关) + `OPENAI_API_KEY` 跑 Qwen chat；后端有 `python-multipart`/`requests`；无 dashscope/ffmpeg。FastAPI（api_server.py）。

## Goals / Non-Goals

**Goals**：`/api/asr` 收录音→千问 ASR→`{text}`；尽量复用现有网关、零/少新依赖；前端按既定契约只换 transcribe 一处。
**Non-Goals**：不改前端交互；不做流式 ASR；不擅自引入 DashScope SDK / ffmpeg（除非 spike 必需）。

## 契约（与 Layer 1 共享，定死）

```
POST /api/asr
  Content-Type: multipart/form-data
    audio:  <file>     # 录音 Blob（MediaRecorder 产出）
    format: <string>   # MediaRecorder.mimeType，如 "audio/webm;codecs=opus"
→ 200 application/json
    { "text": "我今天午餐吃了鸡胸肉和糙米饭", "duration_ms": 3200, "model": "qwen3-asr-flash" }
→ 4xx { "error": "无音频/格式不支持/超出时长" }
→ 5xx { "error": "ASR 服务异常" }
  限制：时长 ≤ ASR_MAX_SECONDS(默认 60)、大小 ≤ ASR_MAX_MB(默认 10)
```
> Layer 1 的 mock 返回**同样的 `{text, duration_ms?}` 结构**，故前端对结果的处理与 Layer 2 完全一致。

## Decisions

- **D1 复用网关、适配器隔离**：`agents/asr.py: transcribe_audio(data, mime, filename) -> {text, duration_ms, model}`；具体调用方式藏在适配器内，由 `ASR_MODE` 配置切换，路由层不感知。
- **D2 首选「OpenAI 音频接口」路径①**：`POST {ASR_BASE_URL}/audio/transcriptions`（multipart：file=Blob 原字节、model=ASR_MODEL）。Whisper 风格接口通常**直收 webm/opus/mp3/m4a，免转码** → 规避最大风险。用 `requests` 直发（无新依赖）。
- **D3 兜底「qwen-audio 多模态 chat」路径②**：`POST {ASR_BASE_URL}/chat/completions`，message 含 `input_audio`(base64 data URI) + 文本提示"逐字转写，仅输出文本"，模型用 qwen-audio 系。当路径①网关不支持时启用（base64 内联，免 OSS）。
- **D4 配置**：`ASR_MODE`(transcriptions|chat_audio|dashscope，spike后默认 chat_audio)、`ASR_MODEL`(默认 qwen3-omni-flash)、`ASR_BASE_URL`/`ASR_API_KEY`(默认复用 OPENAI_*)、`ASR_MAX_SECONDS`/`ASR_MAX_MB`。
- **D5 同步一次性**：短语音(≤60s)同步调用直接返回 text；不做流式/轮询。
- **D6 转码仅在必要时**：路径①免转码；若选路径②/DashScope 且网关只收 wav，再加 ffmpeg+pydub 把 webm/opus→16k mono wav（届时新增依赖并在 proposal 标注）。

## 路由（api_server.py）

> 注：Vite dev proxy 规则 `rewrite: (path) => path.replace(/^\/api/, '')`，即前端 `fetch('/api/asr')` → 后端收到 `POST /asr`。与 `/chat`、`/plan` 等端点保持一致。

```
@app.post("/asr")
async def asr(audio: UploadFile = File(...), format: str = Form(default="")):
    data = await audio.read()
    # 大小/时长上限校验 → 超限 422
    res = await asyncio.to_thread(transcribe_audio, data, format or audio.content_type, audio.filename)
    return res   # {text, duration_ms, model}   异常 → HTTPException(4xx/5xx, {error})
```

## Risks / Trade-offs
- [**主未知**：apiyi 网关是否提供千问 ASR、走哪个端点、收哪些格式] → **落地前先 spike**（task 0）：用 curl 试 `/audio/transcriptions` + 一段 webm，确认 model 别名与返回；不行再试路径②；都不行则退 DashScope 直连(新增 dep)。
- [浏览器 mimeType 差异 webm/opus vs mp4/aac] → format 透传后端；路径① Whisper 多格式兼容性高。
- [安全上下文] → 生产 HTTPS 才能 getUserMedia（前端/部署侧）。
- [时长/大小] → 服务端兜底上限，防大文件；前端也限录音时长。
- [计费/限速] → 复用网关额度；短语音成本低。

## Migration Plan
- 纯新增端点 + 配置；前端改一处 transcribe。无 DDL。
- 回滚：前端 transcribe 切回 mock 即恢复 Layer 1；后端端点保留无害。

## Open Questions
1. spike 结论：路径① 还是 ② 还是 DashScope？→ **路径② chat_audio**（apiyi 网关 `/audio/transcriptions` 返回 404；`/chat/completions` + `input_audio` 可用）
2. `ASR_MODEL` 取什么别名？→ **qwen3-omni-flash**（spike 验证可用，网关模型列表中确认）
3. 是否要把识别文本做轻量后处理（去首尾语气词/标点规整）？默认不做。
