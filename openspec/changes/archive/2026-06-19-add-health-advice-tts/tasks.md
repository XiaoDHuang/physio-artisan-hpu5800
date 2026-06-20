## 1. 后端 TTS

- [x] 1.1 在 `langgraph_config.py` 新增 TTS 配置项（TTS_MODEL/VOICE/BASE_URL/API_KEY/MAX_CHARS）
- [x] 1.2 创建 `backend/agents/tts.py`，`synthesize_speech(text) -> bytes`，路径① `/audio/speech` + 路径② chat_audio_out 兜底，带 429 重试
- [x] 1.3 在 `api_server.py` 新增 `POST /tts` 端点，返回 `audio/mpeg`

## 2. composable（composables/useSpeechSynthesis.ts）

- [x] 2.1 创建 `useSpeechSynthesis.ts`，状态 `isSpeaking` + `isLoading`
- [x] 2.2 `speak(text)` Layer 2 主路径：`fetch('/api/tts')` → Audio 播放；失败自动降级 Layer 1 浏览器 TTS
- [x] 2.3 `stop()`：停止 Audio + speechSynthesis.cancel()，重置 isSpeaking/isLoading
- [x] 2.4 `isLoading` 在 fetch 开始设为 true，`play()` 成功后或 catch 中设为 false
- [x] 2.5 `onUnmounted` 时 `stop()`，防止组件卸载后语音残留

## 3. 组件改动（components/report/HealthAdviceCard.vue）

- [x] 3.1 import `useSpeechSynthesis`，解构 `isSpeaking/isLoading/speak/stop`
- [x] 3.2 每条 `.advice-card` 标题行 flex：左侧标题 + 右侧喇叭 SVG 按钮
- [x] 3.3 喇叭按钮三态：空闲（喇叭+声波）、loading（旋转圆圈 spinner）、播放中（喇叭+竖线+wobble 动画）
- [x] 3.4 loading 期间按钮 disabled，阻止重复点击
- [x] 3.5 点击事件：`toggleSpeak(key, text)`

## 4. 自测

- [x] 4.1 点击喇叭 → loading 圆圈 → 大模型 TTS 播放，图标摆动
- [x] 4.2 播放中再点同一喇叭 → 停止，图标恢复静止
- [x] 4.3 卡片 A 播放中点卡片 B 喇叭 → A 停 B 进入 loading 再播放
- [x] 4.4 切换页面 → 朗读停止，无残留
- [x] 4.5 后端不可用 → 自动降级浏览器 TTS
