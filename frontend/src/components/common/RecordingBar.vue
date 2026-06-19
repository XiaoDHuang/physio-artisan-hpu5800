<script setup lang="ts">
// 录音条：录音中 / 识别中 / 错误 三态。配色走全局 CSS 变量（绿色主色系）。
import type { VoiceState } from '@/composables/useVoiceInput'

defineProps<{
  state: VoiceState
  durationMs: number
  levels: number[]
  errorMsg: string
}>()
defineEmits<{ (e: 'stop'): void; (e: 'cancel'): void }>()

function fmt(ms: number): string {
  const s = Math.floor(ms / 1000)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
</script>

<template>
  <div class="rec-bar" :class="state">
    <!-- 录音中 -->
    <template v-if="state === 'recording'">
      <button class="rec-icon-btn cancel" title="取消" @click="$emit('cancel')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" />
        </svg>
      </button>

      <span class="rec-dot" />
      <span class="rec-label">正在聆听…</span>

      <div class="rec-wave">
        <span
          v-for="(l, i) in levels"
          :key="i"
          class="rec-bar-line"
          :style="{ height: (12 + l * 88) + '%' }"
        />
      </div>

      <span class="rec-time">{{ fmt(durationMs) }}</span>

      <button class="rec-icon-btn stop" title="完成" @click="$emit('stop')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="5 12 10 17 19 7" />
        </svg>
      </button>
    </template>

    <!-- 识别中 -->
    <template v-else-if="state === 'transcribing'">
      <span class="rec-spinner" />
      <span class="rec-label">识别中…</span>
    </template>

    <!-- 错误 -->
    <template v-else>
      <svg class="rec-warn" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M12 9v4" /><circle cx="12" cy="16" r="0.5" fill="currentColor" />
        <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      </svg>
      <span class="rec-label err">{{ errorMsg || '识别失败' }}</span>
    </template>
  </div>
</template>

<style scoped>
.rec-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 84px;
  margin-top: 10px;
  padding: 0 16px;
  border: 1px solid var(--c-primary);
  border-radius: 16px;
  background: var(--c-primary-soft);
}
.rec-bar.error {
  border-color: #e6b8b8;
  background: #fbe9e9;
}
.rec-icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
.rec-icon-btn svg {
  width: 18px;
  height: 18px;
}
.rec-icon-btn.cancel {
  background: #fff;
  color: var(--c-text-tertiary);
}
.rec-icon-btn.cancel:hover {
  color: #d65a5a;
}
.rec-icon-btn.stop {
  background: var(--c-primary);
  color: #fff;
}
.rec-icon-btn.stop:hover {
  background: var(--c-primary-hover);
}
.rec-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #e36a6a;
  flex-shrink: 0;
  animation: recPulse 1.1s ease-in-out infinite;
}
@keyframes recPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.35; transform: scale(0.7); }
}
.rec-label {
  font-size: 13px;
  color: var(--c-text-secondary);
  white-space: nowrap;
}
.rec-label.err {
  color: #d65a5a;
}
.rec-wave {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 32px;
  min-width: 0;
}
.rec-bar-line {
  width: 3px;
  border-radius: 2px;
  background: var(--c-primary);
  transition: height 0.08s linear;
}
.rec-time {
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  color: var(--c-text);
  flex-shrink: 0;
  min-width: 34px;
  text-align: right;
}
.rec-spinner {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--c-primary-soft);
  border-top-color: var(--c-primary);
  animation: recSpin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes recSpin {
  to { transform: rotate(360deg); }
}
.rec-warn {
  width: 18px;
  height: 18px;
  color: #d65a5a;
  flex-shrink: 0;
}
</style>
