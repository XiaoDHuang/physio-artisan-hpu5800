<script setup lang="ts">
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { formatCnDate } from '@/copy/reportChat'

const chat = useChatStore()

const visible = computed(() => chat.activeReportTask !== null)

const isRunning = computed(() => chat.activeReportTask?.status === 'running')

const line = computed(() => {
  const t = chat.activeReportTask
  if (!t) return ''
  if (t.status === 'running') {
    return `${formatCnDate(t.anchorDate)}报告生成中 · ${t.progressLine}`
  }
  return t.bannerLine
})

const tone = computed(() => {
  const s = chat.activeReportTask?.status
  if (s === 'failed') return 'fail'
  if (s === 'timeout') return 'wait'
  if (s === 'completed') return 'ok'
  return 'run'
})
</script>

<template>
  <transition name="fade">
    <div v-if="visible" class="report-task-banner" :class="tone">
      <svg
        v-if="isRunning"
        class="banner-spinner"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" stroke-opacity="0.25" />
        <path d="M12 3a9 9 0 0 1 9 9" stroke-linecap="round" />
      </svg>
      <span class="banner-text">{{ line }}</span>
      <span v-if="isRunning" class="banner-dots" aria-hidden="true">
        <i /><i /><i />
      </span>
    </div>
  </transition>
</template>

<style scoped>
.report-task-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  line-height: 1.5;
  padding: 8px 12px;
  border-radius: 10px;
  margin-top: 10px;
  margin-bottom: 10px;
}
.report-task-banner.run {
  background: #eef8f3;
  color: var(--c-primary-hover);
}
.report-task-banner.ok {
  background: #eef8f3;
  color: #237804;
}
.report-task-banner.fail {
  background: #fff2f0;
  color: #cf1322;
}
.report-task-banner.wait {
  background: #fffbe6;
  color: #ad6800;
}
.banner-text {
  flex: 1;
  min-width: 0;
}
.banner-spinner {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  animation: spin 0.9s linear infinite;
}
.banner-dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
  height: 16px;
}
.banner-dots i {
  display: block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.35;
  animation: dotPulse 1.2s ease-in-out infinite;
}
.banner-dots i:nth-child(2) {
  animation-delay: 0.15s;
}
.banner-dots i:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}
@keyframes dotPulse {
  0%,
  80%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-3px);
  }
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
