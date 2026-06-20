# voice-input-ui Specification

## Purpose

在 `/report`（ChatDock）与 `/nutrition`（NutritionChatDock）提供语音输入：真录音、波形、计时、停止/取消，转写结果追加到输入框。

## Requirements

### Requirement: 聊天框语音输入触发与状态

系统 SHALL 在 `/report`（ChatDock）与 `/nutrition`（NutritionChatDock）聊天框提供语音输入：点击各自的语音图标进入录音（真实 `getUserMedia`+`MediaRecorder`），录音中显示录音条（波形 + 计时 + 停止 + 取消），点击停止进入识别态，识别完成把文本回填输入框。触发为「点击切换」（点击开始、再点停止）。

#### Scenario: 点击语音图标开始录音

- **WHEN** 用户在任一聊天框点击语音图标且授予麦克风权限
- **THEN** 输入区切换为录音条，显示实时波形与计时 `mm:ss`，麦克风持续采集

#### Scenario: 停止后进入识别再回填

- **WHEN** 录音中点击「停止」
- **THEN** 录音条进入「识别中…」态，经 `POST /api/asr` 转写后把文本**追加**进输入框（保留原有文字），状态回到 idle，用户可编辑后再发送

#### Scenario: 取消丢弃

- **WHEN** 录音中点击「取消(✕)」
- **THEN** 停止录音且不转写、不改输入框，释放麦克风，回到 idle

### Requirement: 转写经后端 ASR

系统 SHALL 真实录音并生成音频 `Blob`，默认经 `POST /api/asr` 转写；`transcribe(blob)` 为唯一替换点（`VOICE_USE_MOCK=true` 时可本地 mock 演示）。

#### Scenario: 真实 ASR 转写

- **WHEN** 停止录音且 `VOICE_USE_MOCK=false`
- **THEN** 前端 `POST /api/asr` 上传音频并回填 `text`

### Requirement: 降级与互斥

系统 SHALL 在无麦克风 / 权限拒绝 / 浏览器不支持 `MediaRecorder` 或非安全上下文时显示友好错误并回到 idle，不卡死；语音与发送互斥：`chat.sending` 时禁语音，录音/识别中禁发送与输入；停止/取消/组件卸载时 SHALL 释放麦克风轨道与音频上下文。

#### Scenario: 权限拒绝降级

- **WHEN** 用户拒绝麦克风权限或设备不可用
- **THEN** 录音条显示错误提示，短暂后回到 idle，输入框可正常文字输入

#### Scenario: 资源释放

- **WHEN** 录音停止/取消或聊天框卸载
- **THEN** MediaStream 轨道与 AudioContext 被关闭（麦克风指示灯熄灭），计时/波形循环停止
