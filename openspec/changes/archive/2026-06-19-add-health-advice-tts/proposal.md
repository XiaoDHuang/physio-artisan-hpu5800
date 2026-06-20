## Why

健康建议是 /report 页面的核心信息出口，但目前仅以文字呈现。对于视觉疲劳的用户（尤其是运动后、晚间睡前场景），听比读更自然。利用浏览器内置语音合成（Web Speech API）为三条建议（运动/睡眠/饮食）增加一键播报，零服务端成本，可显著提升信息触达效率。

## What Changes

- 在 `HealthAdviceCard` 的每条建议卡片右上角增加喇叭图标按钮（SVG inline）
- 封装 `useSpeechSynthesis` composable：管理朗读状态、队列、中断逻辑
- 点击喇叭 → 使用 `SpeechSynthesis` 朗读对应建议文本，图标旋转动画表示播放中
- 再次点击喇叭 → 停止朗读，图标恢复静止
- 同一条再次点击 → 从头重新朗读
- 点击其他卡片的喇叭 → 停止当前朗读，开始新的（单例播放，避免重叠）

## Capabilities

### New Capabilities

- `health-advice-tts`: 为健康建议卡片提供文本语音播报能力，包含浏览器 TTS 适配（语速/音量/中文语音选择）、播放状态管理、单例互斥逻辑

### Modified Capabilities

<!-- 无现有 spec 需要修改，纯增量功能 -->

## Impact

- 修改: `frontend/src/components/report/HealthAdviceCard.vue` — 新增喇叭按钮 + 播放状态样式
- 新增: `frontend/src/composables/useSpeechSynthesis.ts` — TTS composable
- 无后端变更（纯浏览器能力）
- 无新增依赖（Web Speech API 为浏览器内置）
