## Why

`/report`（ChatDock）与 `/nutrition`（NutritionChatDock）两个聊天框已有「语音」图标，但只是占位、不可交互。本变更做**第一层：纯前端语音转文字交互**——真录音 + 模拟转写，让用户先看到完整交互效果；第二层（千问 ASR 后端）另起变更，仅替换转写实现，前端零改。

关键设计缝：**录音音频 Blob 是两层之间唯一的接口**。Layer 1 产出真实 Blob 但用 mock 文本，Layer 2 把转写函数换成 `POST /api/asr`。

## What Changes

- 新增 composable `useVoiceInput`（状态机 + `getUserMedia`/`MediaRecorder` 真录音 + 实时波形/计时 + **mock 转写**）。
- 新增共享组件 `components/common/RecordingBar.vue`（录音中/识别中/错误三态 UI：波形 + 计时 + 停止 + 取消）。
- 接入两个聊天框：点击各自已有的「语音」图标 → 触发录音；录音时输入区临时换成 `RecordingBar`；识别完成后**把文本追加进输入框（可编辑、不自动发送）**。
- 触发方式：**点击切换**（点一下开始、再点停止）；桌面端标准。
- 降级：无麦克风 / 权限拒绝 / 浏览器不支持 → 友好提示并回到 idle；与 `chat.sending` 互斥（发送中禁语音、录音/识别中禁发送）。

> 非目标：不接后端、不调真实 ASR（`transcribe(blob)` 内部为 mock）、不自动发送、不改 `/chat` 发送逻辑、不改两个 dock 的整体布局（仅点亮已存在的语音图标 + 覆盖一条录音条）。

## Capabilities

### New Capabilities
- `voice-input-ui`: 聊天框语音转文字前端交互（录音状态机 + 录音条 UI + 文本回填输入框），两个 dock 复用；转写本期为 mock。

### Modified Capabilities
<!-- 无：ChatDock/NutritionChatDock 未建 spec；本变更只点亮其既有语音图标，不改其需求。 -->

## Impact

- **代码（仅 frontend/src）**：新增 `composables/useVoiceInput.ts`、`components/common/RecordingBar.vue`；改 `components/report/ChatDock.vue`、`components/nutrition/NutritionChatDock.vue`（接线语音触发 + 录音条 + 回填）。
- **依赖**：无新增（用浏览器原生 `getUserMedia`/`MediaRecorder`/`AudioContext`）。
- **后端**：无。第二层 `add-voice-asr-backend` 再做 `/api/asr` + 千问 ASR。
- **契约预定**：`transcribe(blob)` 为两层之缝；Blob 的 mimeType 由 `MediaRecorder` 决定（Layer 2 据此处理/转码）。
