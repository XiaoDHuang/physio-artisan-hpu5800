# 实施任务（Layer 1 · 前端语音转文字·真录音+mock 转写）

> 交付方：实现阶段（退出 explore 后）。约束：仅 frontend/src；不接后端、不调真实 ASR、不自动发送、不改 dock 整体布局与 /chat 逻辑。
> 依据：本变更 design.md（状态机 + composable API + RecordingBar + 两层契约）。

## 1. composable（composables/useVoiceInput.ts）

- [ ] 1.1 状态机 state(idle/requesting/recording/transcribing/error) + durationMs + levels + errorMsg
- [ ] 1.2 start()：选可用 mimeType(`MediaRecorder.isTypeSupported`) → getUserMedia → MediaRecorder.start；AnalyserNode 出 ~16 根波形(rAF 节流)；计时器
- [ ] 1.3 stop()：停止录音 → 取 Blob → await transcribe(blob) → 返回文本；cancel()：停止丢弃不转写
- [ ] 1.4 transcribe(blob)：**本期 mock**（setTimeout~1200ms 返回示例文本；按 dock 可传不同示例集）——标注此处为 Layer 2 替换点
- [ ] 1.5 资源释放：stop/cancel/onUnmounted 关闭 stream 轨道 + AudioContext + 清计时/rAF
- [ ] 1.6 异常：权限拒绝/无设备/不支持 → state=error + errorMsg，超时回 idle

## 2. 录音条（components/common/RecordingBar.vue）

- [ ] 2.1 props(state,durationMs,levels,errorMsg) + emits(stop,cancel)
- [ ] 2.2 recording 态：✕取消 + 波形(levels) + 「正在聆听…」+ mm:ss + ⏹停止
- [ ] 2.3 transcribing 态：⟳ + 「识别中…」（不可操作）；error 态：⚠ + errorMsg
- [ ] 2.4 样式对齐 theme.ts，覆盖在原输入框位置

## 3. 接入 report ChatDock（components/report/ChatDock.vue）

- [ ] 3.1 输入为空时：原右下圆按钮语义切到「麦克风」(点击 start)；有文字时维持发送
- [ ] 3.2 录音/识别中用 RecordingBar 覆盖 textarea 区；监听 stop→回填、cancel→还原
- [ ] 3.3 识别文本 append 进 input（保留原文字 + 空格拼接）；与 chat.sending 互斥

## 4. 接入 nutrition NutritionChatDock（components/nutrition/NutritionChatDock.vue）

- [ ] 4.1 工具行「语音」图标解除 disabled，点击 start；「发送」按钮不变
- [ ] 4.2 录音/识别中 RecordingBar 覆盖 input-box；stop→回填、cancel→还原；互斥同上
- [ ] 4.3 mock 示例文本给饮食场景（如「我午餐吃了鸡胸肉和糙米饭」）

## 5. 自测

- [ ] 5.1 两个聊天框：点语音→授权→看到波形+计时→停止→识别中→文本回填→可编辑发送
- [ ] 5.2 取消、权限拒绝、发送中禁语音/录音中禁发送 均正确
- [ ] 5.3 停止/取消/切页后麦克风指示灯熄灭（无泄漏）
- [ ] 5.4 vue-tsc + vite build 通过；控制台无 error
