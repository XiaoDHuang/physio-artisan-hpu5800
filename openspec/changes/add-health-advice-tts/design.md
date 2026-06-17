## Context

HealthAdviceCard 当前渲染三条纯文本建议（运动/睡眠/饮食），无任何交互。目标是在此基础上增加语音播报。现有语音体系 `useVoiceInput` 是反方向（语音→文本），不适用于本次需求。

## Goals / Non-Goals

**Goals:**
- 每条建议卡片右上角一个喇叭图标按钮，点击后调用后端大模型 TTS 朗读建议文本（Layer 2 主路径）
- 后端 TTS 不可用时自动降级到浏览器 Web Speech API（Layer 1）
- 播放中图标摆动动画，loading 时旋转圆圈，再次点击停止
- 同一时间只允许一条语音播放（单例互斥）
- 大模型 TTS 提供更自然、一致的专业中文语音

**Non-Goals:**
- 不生成新的语音文本（直接用已有建议文本）
- 不改变卡片布局结构和现有样式体系
- 不处理前后台切换时的语音状态

## Decisions

**D1: 两层 TTS 架构（与 voice-input/ASR 同模式）**

| Layer | 描述 | 状态 |
|-------|------|------|
| Layer 1 | 浏览器 Web Speech API，纯前端降级 | 完成 |
| Layer 2 | 后端 `/api/tts` → 大模型 TTS → 返回 mp3 → Audio 播放 | 本期主路径 |

替换点：`useSpeechSynthesis.speak(text)` 优先 `fetch('/api/tts', {body: {text}})` → 获取音频 Blob → `new Audio(url).play()`。失败自动降级 Layer 1。composable 对外接口不变，组件无需改动。

**D2: 封装 `useSpeechSynthesis` composable 而非内联在组件**

组件只处理 UI（点击/样式），语音逻辑集中在 composable：
- `speak(text)` → 优先后端 TTS，失败降级浏览器
- `stop()` → 停止所有播放
- `isSpeaking: Ref<boolean>` → 播放状态
- `isLoading: Ref<boolean>` → 网络请求/合成中状态
- 内部管理 Audio/SpeechSynthesisUtterance 实例，自动处理单例互斥

**D3: 后端 TTS 适配器（`backend/agents/tts.py`）**

对称于 ASR（`agents/asr.py`），路径①：`POST /audio/speech`（OpenAI TTS 接口，返回 mp3 字节）；路径②：chat completions + audio output 兜底。带 429 重试。

**D4: 单例播放 vs 队列**

选单例互斥（新播放自动停止旧播放），不搞队列。三条建议是短文（~100字），没有连续播放需求。

**D5: 喇叭图标三态**

- 空闲：喇叭 + 声波弧线，灰色 `#999`
- loading：旋转圆圈 spinner，0.9s 线性旋转，按钮 disabled
- 播放中：喇叭 + 竖线，对应卡片主题色 + CSS wobble 动画（±18° 摆动）

**D6: 语音选择策略（Layer 1 降级时）**

`speechSynthesis.getVoices()` 同步获取可能为空（浏览器异步加载）。处理方式：
- 首次调用 `speak` 时实时获取 voices 列表
- 优先匹配 `zh-CN`，其次包含 `zh` 的任意语音
- 若都无，使用 `speechSynthesis` 默认语音（通常 OS 语音）

## Risks / Trade-offs

- [R] 网关 `/audio/speech` 不可用 → 自动降级 chat_audio_out 兜底
- [R] 后端完全不可用 → 前端自动降级浏览器 TTS，不白屏
- [R] 部分浏览器（如 Firefox）中文语音不可用 → Layer 1 降级时用系统自带语音
- [R] iOS Safari 的 SpeechSynthesis 在静音模式下不发声 → 浏览器原生限制
- [R] `onend` 事件在后台 tab 可能不触发 → 以 Audio 的 onended 为主（更可靠）
