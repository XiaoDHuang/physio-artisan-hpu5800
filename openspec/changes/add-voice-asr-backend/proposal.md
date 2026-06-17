## Why

第二层：把聊天框语音输入的「转写」从 Layer 1 的 mock 换成**千问语音识别后端**。前端按 `add-voice-input-mock` 已定的契约只改一处（`transcribe(blob)` 由 mock 改为 `POST /api/asr`），其余零改。

现状约束（影响选型）：项目 LLM 走 **OpenAI 兼容网关**（`OPENAI_BASE_URL`，第三方聚合，非直连 DashScope）；后端已装 `python-multipart`、`requests`；**无 `dashscope` SDK、无 ffmpeg**。因此优先**复用同一网关**做 ASR，避免新引 SDK/系统依赖。

## What Changes

- 新增端点 `POST /api/asr`（FastAPI `UploadFile` 多部分表单）：收录音 Blob → 调千问 ASR → 返回 `{ text, duration_ms?, model }`。
- 新增 `backend/agents/asr.py`：`transcribe_audio(data: bytes, mime: str, filename: str) -> dict`，**适配器**封装具体 ASR 调用，模型/路径可配。
- **首选实现路径**：经 `OPENAI_BASE_URL` 网关调千问语音模型。两条候选（落地前 spike 二选一）：
  - 路径①（首选）`POST {base_url}/audio/transcriptions`（OpenAI 音频接口，`model=ASR_MODEL`，file=原始 Blob）——Whisper 风格通常**直收 webm/opus，免转码**。
  - 路径②（兜底）`POST {base_url}/chat/completions` 多模态 `input_audio`(base64) + qwen-audio 模型，提示"逐字转写"。
- 配置：`ASR_MODEL`（默认如 `qwen3-asr-flash`/网关提供的千问 ASR 别名）、可选 `ASR_BASE_URL`/`ASR_API_KEY`（默认复用 `OPENAI_*`）、`ASR_MAX_SECONDS`/大小上限。
- 前端切换：`useVoiceInput.transcribe(blob)` 内部 mock → `fetch('/api/asr', FormData)`；契约不变。
- 降级：无音频/超限/格式不支持/ASR 报错 → 4xx/5xx `{error}`，前端回 idle 提示。

> 非目标：不改前端交互/录音逻辑（仅替换 transcribe 一处）；不引入 DashScope SDK（除非 spike 证明网关不支持千问 ASR，才退而单列）；不做流式/实时 ASR（短语音一次性同步即可）。

## Capabilities

### New Capabilities
- `voice-asr-api`: `POST /api/asr` 语音转文字端点（千问 ASR 适配器 + 配置 + 降级），与 `voice-input-ui` 契约对接。

### Modified Capabilities
<!-- 无 spec 增量：voice-input-ui 由 add-voice-input-mock 引入，本层只在集成任务里把其
     transcribe 从 mock 切到 /api/asr（响应结构不变、前端处理一致），不改其需求文本。
     依赖：本变更应在 add-voice-input-mock 之后落地/归档。 -->


## Impact

- **代码**：`backend/api_server.py`（`/api/asr` 路由 + 登记）、`backend/agents/asr.py`（适配器）、`backend/config/langgraph_config.py`（ASR_* 配置项）；前端 `composables/useVoiceInput.ts`（transcribe 换实现）。
- **依赖**：首选路径无新增（用 `requests`/`httpx` 走现有网关）；若 spike 选 DashScope 直连则新增 `dashscope`；若需转码则新增 `ffmpeg`（系统依赖）+ `pydub`——均待 spike 后定。
- **配置/部署**：新增 `ASR_MODEL` 等 env；生产麦克风需 HTTPS（前端侧约束）。
- **风险**：网关是否提供千问 ASR 及其端点/格式 = 主未知，落地前先 spike。
