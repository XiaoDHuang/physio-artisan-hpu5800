## Context

两个聊天框现状：
- `report/ChatDock.vue`：右下圆按钮重载——有文字=发送、空=语音(占位)；`voice.png` 常显。
- `nutrition/NutritionChatDock.vue`：工具行独立「语音」图标(disabled) + 单独「发送」长按钮。
- 二者都用同一个 `useChatStore`（单轮覆盖式 `send(text)`）。语音只是输入法，产出文本进同一发送流程。

## Goals / Non-Goals

**Goals**：纯前端跑通「点麦克风→录音(真)→识别(mock)→文本回填输入框」完整交互；两个 dock 复用同一套逻辑/组件；为 Layer 2 留好 Blob 接口。
**Non-Goals**：不接后端/真实 ASR；不自动发送；不改 dock 布局与 `/chat` 逻辑。

## Decisions

- **D1 真录音 + mock 转写**：用 `getUserMedia({audio})` + `MediaRecorder` 真录，`AudioContext`+`AnalyserNode` 出实时波形；`transcribe(blob)` 内部 `setTimeout(~1200ms)` 返回轮播假文本。备选「完全假」否决——看不到权限/波形，且 Layer 2 返工大。
- **D2 文本回填、不自动发送**：识别结果**追加**进输入框（保留已有文字 + 空格拼接），用户可编辑后再发。贴合饮食页「识别食物→我午餐吃了…→发送」。
- **D3 点击切换触发**：点麦=开始，再点=停止识别；另设取消(✕)丢弃。桌面端标准（非按住说话）。
- **D4 各 dock 保留布局**：只点亮既有语音图标做触发；录音时用 `RecordingBar` 覆盖输入区。
  - report：输入框为空时，原重载按钮作「麦克风」(点击录音)；有文字时仍是「发送」。
  - nutrition：工具行「语音」图标解除 disabled，点击录音；「发送」按钮不变。
- **D5 互斥**：`chat.sending` 时禁语音；录音/识别中禁发送与输入。

## composable：`composables/useVoiceInput.ts`

```ts
type VoiceState = 'idle' | 'requesting' | 'recording' | 'transcribing' | 'error'

useVoiceInput() => {
  state: Ref<VoiceState>
  durationMs: Ref<number>      // 录音计时（RecordingBar 显示 00:03）
  levels: Ref<number[]>        // 0~1 的若干根波形条（AnalyserNode 采样）
  errorMsg: Ref<string>
  start(): Promise<void>       // getUserMedia → MediaRecorder.start + 计时/波形循环
  stop(): Promise<string>      // 停止 → 拿 Blob → transcribe(blob) → 返回文本
  cancel(): void               // 停止并丢弃，不转写
}
```
- `transcribe(blob: Blob): Promise<string>` —— **两层之缝**。Layer 1 = mock；Layer 2 = `fetch('/api/asr', {body: FormData(audio=blob)})`。
- 资源清理：stop/cancel/卸载时关闭 MediaStream 轨道、AudioContext、清计时器（防麦克风指示灯常亮）。
- 异常：权限拒绝/无设备/`MediaRecorder` 不支持 → `state='error'` + `errorMsg`，3 态后回 idle。

## 组件：`components/common/RecordingBar.vue`

- props：`state`、`durationMs`、`levels`、`errorMsg`
- emits：`stop`、`cancel`
- 渲染：
  - recording：✕(cancel) + 波形(levels) + 「正在聆听…」+ `mm:ss` + ⏹(stop)
  - transcribing：⟳ +「识别中…」（不可操作）
  - error：⚠ + errorMsg（点任意处/超时回 idle）
- 尺寸/圆角/主色对齐 `theme.ts`，覆盖在原输入框位置。

## 两层契约（权威定义见 `add-voice-asr-backend`；Layer 1 mock 严格对齐它）

```
Layer 2 端点（Layer 1 的 mock 返回同样的成功结构）：
  POST /api/asr   multipart/form-data { audio: <blob>, format: <mediaRecorder.mimeType> }
  → 200 { text: string, duration_ms?: number, model?: string }
  → 4xx/5xx { error: string }
```
- **mock 对齐**：Layer 1 的 `transcribe(blob)` 返回 `{ text, duration_ms? }`（与 `/api/asr` 200 同构），
  故前端对结果/错误的处理在两层完全一致。Layer 2 只把函数体从「setTimeout 返回假对象」换成
  「`fetch('/api/asr', FormData(audio=blob, format=mimeType))` 解析同结构」。
- 回填：`input += (input ? ' ' : '') + result.text`。
- Blob 的 mimeType 由 `MediaRecorder` 决定并随 `format` 传后端，供 Layer 2 处理/转码判断。

## 各 dock 接入点

| dock | 触发 | 录音 UI | 回填 |
|---|---|---|---|
| ChatDock | 输入空→原圆按钮=麦克风(点击 start)；有字→维持发送 | RecordingBar 覆盖 textarea 区 | 文本 append 进 `input` |
| NutritionChatDock | 工具行「语音」图标解禁→点击 start | RecordingBar 覆盖 input-box | 文本 append 进 `input` |

## Risks / Trade-offs
- [getUserMedia 需安全上下文] → dev=localhost 可用；生产需 HTTPS（记入 Layer 2 / 部署）。
- [浏览器 mimeType 差异：Chrome webm/opus、Safari mp4] → composable 选可用 mimeType（`MediaRecorder.isTypeSupported`），并把 mimeType 传给 Layer 2。
- [波形性能] → AnalyserNode 取 ~16 根条、`requestAnimationFrame` 节流；卸载即停。
- [麦克风指示灯常亮] → 严格在 stop/cancel/unmount 释放 track。
- [mock 文本被误认为真识别] → 文案可加「(示例)」前缀或控制台提示，Layer 2 去除。

## Open Questions
1. mock 文本用固定一句还是按 dock 不同（报告页通用 / 饮食页给「我午餐吃了…」类）？倾向按 dock 给不同示例集。
2. report 空输入时是否真把圆按钮语义切到「麦克风」，还是新增一个独立小麦克风图标？倾向语义切换（不增按钮）。
3. 是否需要「上滑取消」等手势？本期 desktop 用显式 ✕ 取消即可，手势略。
