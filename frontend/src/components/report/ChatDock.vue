<script setup lang="ts">
// 底部聊天卡片：机器人问候 + 建议气泡 + 输入框（底部工具条）+ 回复（在输入框下方）
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { ChatSendContext } from '@/stores/chat'
import { looksLikeReportRequest, formatCnDate } from '@/copy/reportChat'
import ReportTaskBanner from '@/components/common/ReportTaskBanner.vue'
import robot from '@/assets/chat/robot.png'
import iconPlus from '@/assets/chat/attachment-plus.png'
import iconImage from '@/assets/chat/图片识别.png'
import iconVideo from '@/assets/chat/视频上传.png'
import iconVoice from '@/assets/chat/voice.png'
import RecordingBar from '@/components/common/RecordingBar.vue'
import { useVoiceInput } from '@/composables/useVoiceInput'

const props = defineProps<{
  userId?: number
  reportDate?: string
  userName?: string
  onReportComplete?: () => void | Promise<void>
}>()

const chat = useChatStore()
const input = ref('')

const reportGenerateSuggestion = computed(() => {
  const d = props.reportDate?.trim()
  if (!d) return '帮我生成今天的健康体检报告'
  const day = formatCnDate(d)
  return day === '今天' ? '帮我生成今天的健康体检报告' : `帮我生成${day}的健康体检报告`
})

const suggestions = computed(() => [
  reportGenerateSuggestion.value,
  '如何提升睡眠质量？',
  '适合我的减脂计划是什么？',
])

function chatCtx(): ChatSendContext {
  return {
    userId: props.userId,
    date: props.reportDate,
    userName: props.userName,
    onReportComplete: props.onReportComplete,
  }
}

function suggestDisabled(text: string) {
  return chat.sending || (chat.isReportRunning && looksLikeReportRequest(text))
}

async function send(text: string) {
  const t = text.trim()
  if (!t || chat.sending) return
  await chat.send(t, chatCtx())
}

async function onSend() {
  const t = input.value.trim()
  if (!t || chat.sending) return
  input.value = ''
  await send(t)
}

function onEnter(e: KeyboardEvent) {
  if (e.shiftKey) return // Shift+Enter 换行
  e.preventDefault()
  onSend()
}

// 语音输入：空输入时点圆按钮=录音；有文字时=发送
const {
  state: voiceState,
  durationMs: voiceDuration,
  levels: voiceLevels,
  errorMsg: voiceError,
  start: voiceStart,
  stop: voiceStop,
  cancel: voiceCancel,
} = useVoiceInput({
  mockSamples: [
    '（语音示例）如何提升我的睡眠质量？',
    '（语音示例）帮我看看今天的运动达标了吗？',
    '（语音示例）最近压力有点大，有什么调节建议？',
  ],
})

function onMicOrSend() {
  if (input.value.trim()) {
    onSend()
    return
  }
  if (chat.sending) return
  voiceStart()
}

async function onVoiceStop() {
  const text = await voiceStop()
  if (text) input.value = input.value ? `${input.value} ${text}` : text
}
</script>

<template>
  <div class="chat-card">
    <!-- 顶部：机器人头像 + 问候 + 建议气泡 -->
    <div class="chat-head">
      <img :src="robot" class="robot" alt="助手" />
      <div class="head-main">
        <div class="greeting">Hi！我是你的健康助手，有什么可以帮你的吗？</div>
        <div class="suggestions">
          <button
            v-for="s in suggestions"
            :key="s"
            class="suggest-pill"
            :disabled="suggestDisabled(s)"
            @click="send(s)"
          >
            {{ s }}
          </button>
        </div>
      </div>
    </div>

    <ReportTaskBanner />

    <!-- 输入框（含底部工具条）/ 录音条 -->
    <div v-if="voiceState === 'idle'" class="input-box">
      <textarea
        v-model="input"
        class="input-area"
        placeholder="发消息"
        rows="2"
        :disabled="chat.sending"
        @keydown.enter="onEnter"
      />
      <div class="toolbar">
        <div class="tools-left">
          <button class="tool-icon-btn" title="添加附件（占位）" disabled>
            <img :src="iconPlus" class="tool-img" alt="" />
          </button>
          <span class="divider" />
          <button class="tool-text-btn" title="图片识别（占位）" disabled>
            <img :src="iconImage" class="tool-img" alt="" /> 图片识别
          </button>
          <button class="tool-text-btn" title="视频上传（占位）" disabled>
            <img :src="iconVideo" class="tool-img" alt="" /> 视频上传
          </button>
        </div>
        <button
          class="voice-btn"
          :class="{ active: input.trim() }"
          :title="input.trim() ? '发送' : '语音输入'"
          @click="onMicOrSend"
        >
          <img :src="iconVoice" class="voice-img" alt="" />
        </button>
      </div>
    </div>
    <RecordingBar
      v-else
      :state="voiceState"
      :duration-ms="voiceDuration"
      :levels="voiceLevels"
      :error-msg="voiceError"
      @stop="onVoiceStop"
      @cancel="voiceCancel"
    />

    <!-- 机器人回复（输入框下方，覆盖式单条）-->
    <transition name="fade">
      <div v-if="chat.sending || chat.lastReply" class="reply-bar">
        <span class="reply-tag">AI</span>
        <span v-if="chat.sending" class="reply-text thinking">正在理解你的需求…</span>
        <span v-else class="reply-text" :class="{ blocked: chat.lastIntent === 'blocked' }">{{ chat.lastReply }}</span>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.chat-card {
  flex-shrink: 0;
  margin-top: 16px;
  background: var(--c-card-bg);
  border-radius: 18px;
  box-shadow: 0 4px 18px rgba(31, 45, 40, 0.07);
  padding: 18px 22px 20px;
}

/* 顶部问候区 */
.chat-head {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.robot {
  width: 64px;
  height: 64px;
  object-fit: contain;
  flex-shrink: 0;
}
.head-main {
  flex: 1;
  min-width: 0;
}
.greeting {
  font-size: 16px;
  color: var(--c-text-secondary);
  margin: 8px 0 14px;
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}
.suggest-pill {
  padding: 10px 22px;
  border: 1px solid var(--c-primary);
  background: #fff;
  color: var(--c-primary-hover);
  border-radius: 22px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.suggest-pill:hover:not(:disabled) {
  background: var(--c-primary-soft);
}
.suggest-pill:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 输入框 */
.input-box {
  margin-top: 18px;
  border: 1px solid #d8ece4;
  border-radius: 16px;
  padding: 14px 16px 10px;
  transition: border-color 0.15s;
}
.input-box:focus-within {
  border-color: var(--c-primary);
}
.input-area {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.6;
  color: var(--c-text);
  background: transparent;
  font-family: inherit;
}
.input-area::placeholder {
  color: var(--c-text-tertiary);
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}
.tools-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.tool-icon-btn,
.tool-text-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--c-text-secondary);
  font-size: 14px;
  cursor: not-allowed;
  padding: 4px 2px;
}
.tool-img {
  width: 20px;
  height: 20px;
  object-fit: contain;
}
.divider {
  width: 1px;
  height: 18px;
  background: var(--c-border);
}
.voice-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: #eef3f1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s;
}
.voice-btn.active {
  background: var(--c-primary-soft);
}
.voice-img {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

/* 回复 */
.reply-bar {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: var(--c-primary-soft);
  border-radius: 12px;
  padding: 12px 14px;
  margin-top: 14px;
}
.reply-tag {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--c-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.reply-text {
  font-size: 14px;
  color: var(--c-text);
  line-height: 1.6;
  white-space: pre-wrap;
}
.reply-text.thinking {
  color: var(--c-text-tertiary);
}
.reply-text.blocked {
  color: #d4380d;
  font-weight: 600;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
