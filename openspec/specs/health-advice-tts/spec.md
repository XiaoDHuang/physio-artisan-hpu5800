# health-advice-tts Specification

## Purpose

健康建议卡片语音播报：优先大模型 TTS，降级浏览器 SpeechSynthesis。

## Requirements

### Requirement: 建议卡片语音播报按钮

每个健康建议卡片（运动建议、睡眠建议、饮食建议）的右上角 SHALL 显示一个喇叭图标按钮，用户点击后调用后端大模型 TTS 朗读对应建议文本，后端不可用时自动降级到浏览器语音合成。

#### Scenario: 点击喇叭开始大模型朗读

- **WHEN** 用户点击静止状态的喇叭按钮且后端 TTS 可用
- **THEN** 按钮显示 loading 旋转圆圈动画，按钮 disabled
- **AND** 后端合成 mp3 成功后 loading 结束，开始播放，喇叭图标进入摆动动画状态
- **AND** 其他卡片若有正在播放的语音，自动停止

#### Scenario: 点击喇叭降级浏览器朗读

- **WHEN** 用户点击喇叭按钮且后端 TTS 不可用
- **THEN** loading 状态结束后自动降级到浏览器 SpeechSynthesis 朗读
- **AND** 喇叭图标进入摆动动画状态

#### Scenario: 播放中再次点击停止

- **WHEN** 用户点击正在播放中的喇叭按钮
- **THEN** 当前朗读停止
- **AND** 喇叭图标恢复静止状态

#### Scenario: 点击其他卡片喇叭

- **WHEN** 卡片 A 正在朗读中，用户点击卡片 B 的喇叭按钮
- **THEN** 卡片 A 的朗读停止，A 的图标恢复静止
- **AND** 卡片 B 进入 loading 然后开始朗读

### Requirement: Loading 状态

喇叭按钮在等待后端 TTS 响应期间 SHALL 显示 loading 旋转圆圈动画，且按钮处于 disabled 状态，防止重复点击。

#### Scenario: 后端响应中显示 loading

- **WHEN** 用户点击喇叭按钮
- **THEN** 图标立即切换为旋转圆圈
- **AND** 按钮不可点击
- **AND** 后端响应后恢复为喇叭图标（播放摆动或静止）

### Requirement: 语音输出配置

系统 SHALL 优先使用大模型 TTS 语音播报；降级时使用中文语音，语速 0.9，音量 1.0。

#### Scenario: 大模型 TTS 可用

- **WHEN** 后端 `/api/tts` 正常响应
- **THEN** 使用大模型合成音频（mp3）播放

#### Scenario: 降级时使用中文语音

- **WHEN** 降级到浏览器 SpeechSynthesis
- **THEN** 优先使用 zh-CN 语音，其次使用任意 zh 语音，最后使用默认语音

### Requirement: 单例播放互斥

同一时间全局 SHALL 只允许一条语音播放，任何新播放请求必须停止当前正在播放的语音。

#### Scenario: 新播放自动停止旧播放

- **WHEN** 有语音正在播放时，调用 speak() 传入新文本
- **THEN** 当前播放立即停止
- **AND** 新文本开始合成并播放

### Requirement: 组件卸载资源释放

系统 SHALL 在 `HealthAdviceCard` 组件卸载时停止所有朗读并释放音频资源，防止页面切换后语音残留。

#### Scenario: 页面切换时停止朗读

- **WHEN** 用户从 /report 导航到其他页面且朗读正在进行
- **THEN** 朗读立即停止，audio 元素释放，无残留语音
