## ADDED Requirements

### Requirement: 语音转文字端点 /api/asr
系统 SHALL 提供 `POST /api/asr`（`multipart/form-data`：`audio` 文件 + `format` 字符串），收录音并返回转写文本。响应 200 SHALL 为 `{ "text": string, "duration_ms"?: number, "model": string }`；前端按此结构处理，与 Layer 1 mock 返回结构一致。

#### Scenario: 录音转文字成功
- **WHEN** 前端 `POST /api/asr` 上传一段录音 Blob
- **THEN** 返回 200 且 `text` 为该段语音的转写文本，前端将其回填输入框

#### Scenario: 无音频或超限
- **WHEN** 未带 `audio`、或时长/大小超过 `ASR_MAX_SECONDS`/`ASR_MAX_MB`
- **THEN** 返回 4xx `{ "error": ... }`，不调用 ASR

### Requirement: 千问 ASR 适配器与配置
系统 SHALL 用适配器 `transcribe_audio(data, mime, filename)` 封装 ASR 调用，默认经现有 OpenAI 兼容网关调用千问语音模型，路径由 `ASR_MODE` 配置切换（首选 `transcriptions` 直传 Blob、兜底 `chat_audio` 多模态 base64）。模型与网关 SHALL 可配（`ASR_MODEL` / `ASR_BASE_URL` / `ASR_API_KEY`，默认复用 `OPENAI_*`）。

#### Scenario: 默认走网关 transcriptions 路径
- **WHEN** 未特别配置 `ASR_MODE`
- **THEN** 适配器以 `POST {ASR_BASE_URL}/audio/transcriptions`（model=`ASR_MODEL`、file=原始 Blob）转写，不做格式转码

#### Scenario: 配置切换不影响路由与前端
- **WHEN** 改 `ASR_MODE`/`ASR_MODEL`
- **THEN** `/api/asr` 路由与前端契约不变，仅适配器内部调用方式变化

### Requirement: 失败降级
系统 SHALL 在 ASR 服务异常/格式不支持/网络失败时返回 4xx/5xx `{ "error": ... }`，不抛未捕获异常；前端据此回到 idle 并提示，不影响文字输入与既有 `/chat` 流程。

#### Scenario: ASR 异常返回结构化错误
- **WHEN** 上游 ASR 调用失败
- **THEN** `/api/asr` 返回 5xx `{ "error": ... }`，服务不崩、其余端点不受影响
