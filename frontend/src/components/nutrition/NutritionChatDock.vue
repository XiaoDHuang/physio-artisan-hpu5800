<script setup lang="ts">
// 能康助手：复用 useChatStore 的单轮覆盖交互，按饮食页样式呈现
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import SectionCard from '@/components/report/SectionCard.vue'
import robot from '@/assets/page-nutrition/机器人.png'
import icImage from '@/assets/page-nutrition/图片识别.png'
import icVideo from '@/assets/page-nutrition/视频上传.png'
import icVoice from '@/assets/page-nutrition/语音图标.png'
import icSend from '@/assets/page-nutrition/发送按钮图标.svg'

const chat = useChatStore()
const input = ref('')

const chips = ['AI算热量', '识别食物']

async function send(text: string) {
  const t = text.trim()
  if (!t || chat.sending) return
  await chat.send(t)
}
async function onSend() {
  const t = input.value.trim()
  if (!t || chat.sending) return
  input.value = ''
  await send(t)
}
function onEnter(e: KeyboardEvent) {
  if (e.shiftKey) return
  e.preventDefault()
  onSend()
}
</script>

<template>
  <SectionCard>
    <div class="head">
      <img :src="robot" class="robot" alt="助手" />
      <div class="head-main">
        <div class="greeting">Hi！我是你的能康助手，有什么可以帮你的吗？</div>
        <div class="chips">
          <button v-for="c in chips" :key="c" class="chip" :disabled="chat.sending" @click="send(c)">
            {{ c }}
          </button>
        </div>
      </div>
    </div>

    <div class="input-box">
      <textarea
        v-model="input"
        class="input-area"
        placeholder="发消息"
        rows="2"
        :disabled="chat.sending"
        @keydown.enter="onEnter"
      />
      <div class="tools">
        <button class="tool" title="图片识别（占位）" disabled>
          <img :src="icImage" class="tool-ic" alt="" /> 图片识别
        </button>
        <button class="tool" title="视频上传（占位）" disabled>
          <img :src="icVideo" class="tool-ic" alt="" /> 视频上传
        </button>
        <button class="tool" title="语音（占位）" disabled>
          <img :src="icVoice" class="tool-ic" alt="" />
        </button>
      </div>
    </div>

    <transition name="fade">
      <div v-if="chat.sending || chat.lastReply" class="reply-bar">
        <span class="reply-tag">AI</span>
        <span v-if="chat.sending" class="reply-text thinking">正在思考…</span>
        <span v-else class="reply-text" :class="{ blocked: chat.lastIntent === 'blocked' }">{{ chat.lastReply }}</span>
      </div>
    </transition>

    <button class="send-btn" :disabled="chat.sending" @click="onSend">
      <img :src="icSend" class="send-ic" alt="" /> 发送
    </button>
  </SectionCard>
</template>

<style scoped>
.head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.robot {
  width: 52px;
  height: 52px;
  object-fit: contain;
  flex-shrink: 0;
}
.head-main {
  flex: 1;
  min-width: 0;
}
.greeting {
  font-size: 14px;
  color: var(--c-text-secondary);
  margin: 4px 0 10px;
}
.chips {
  display: flex;
  gap: 10px;
}
.chip {
  padding: 5px 14px;
  border: 1px solid var(--c-primary);
  background: #fff;
  color: var(--c-primary-hover);
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
}
.chip:hover:not(:disabled) {
  background: var(--c-primary-soft);
}
.chip:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.input-box {
  margin-top: 14px;
  border: 1px solid #d8ece4;
  border-radius: 14px;
  padding: 12px 14px 8px;
}
.input-box:focus-within {
  border-color: var(--c-primary);
}
.input-area {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.6;
  color: var(--c-text);
  background: transparent;
  font-family: inherit;
}
.input-area::placeholder {
  color: var(--c-text-tertiary);
}
.tools {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 6px;
}
.tool {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: transparent;
  color: var(--c-text-secondary);
  font-size: 13px;
  cursor: not-allowed;
  padding: 2px;
}
.tool-ic {
  width: 18px;
  height: 18px;
  object-fit: contain;
}
.reply-bar {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: var(--c-primary-soft);
  border-radius: 12px;
  padding: 10px 12px;
  margin-top: 12px;
}
.reply-tag {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: var(--c-primary);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.reply-text {
  font-size: 13px;
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
.send-btn {
  width: 100%;
  margin-top: 14px;
  border: none;
  background: var(--c-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  padding: 11px 0;
  border-radius: 24px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.send-btn:hover:not(:disabled) {
  background: var(--c-primary-hover);
}
.send-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.send-ic {
  width: 18px;
  height: 18px;
  object-fit: contain;
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
