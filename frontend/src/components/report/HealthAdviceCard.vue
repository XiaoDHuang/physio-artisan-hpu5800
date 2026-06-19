<script setup lang="ts">
import { computed, ref } from 'vue'
import type { HealthAdvice } from '@/api/types'
import { useSpeechSynthesis } from '@/composables/useSpeechSynthesis'
import SectionCard from './SectionCard.vue'

const props = defineProps<{
  advice: HealthAdvice | null
  emptyHint?: string
}>()

const { isSpeaking, isLoading, errorMsg, speak, stop } = useSpeechSynthesis()
const activeKey = ref<string | null>(null)

// 占位文案（无报告时显示）
const PLACEHOLDER = {
  exercise: '每日 30 分钟有氧搭配 15 分钟力量，快走、哑铃皆可。足量饮水，循序渐进加量，助力提升肌肉、优化体脂。',
  sleep: '固定 23 点前入睡，每日睡 7–8 小时，睡前少看电子屏、忌浓茶咖啡。卧室避光恒温，规律作息稳代谢。',
  nutrition: '三餐粗细搭配，优质蛋白足量摄入，少油少盐控糖。多吃蔬菜，主食替换杂粮，规律进餐稳血糖。',
}

const cards = computed(() => {
  const hint = props.emptyHint
  const useHint = !props.advice && hint
  return [
    { key: 'exercise', title: '运动建议', cls: 'green', text: props.advice?.exercise || (useHint ? hint : PLACEHOLDER.exercise), btn: '查看运动计划' },
    { key: 'sleep', title: '睡眠建议', cls: 'purple', text: props.advice?.sleep || (useHint ? hint : PLACEHOLDER.sleep), btn: '查看改善方法' },
    { key: 'nutrition', title: '饮食建议', cls: 'orange', text: props.advice?.nutrition || (useHint ? hint : PLACEHOLDER.nutrition), btn: '查看饮食方案' },
  ]
})

function toggleSpeak(key: string, text: string) {
  if (activeKey.value === key && isSpeaking.value) {
    stop()
    activeKey.value = null
  } else {
    stop()
    speak(text)
    activeKey.value = key
  }
}
</script>

<template>
  <SectionCard title="健康建议">
    <div class="advice-grid">
      <div v-for="c in cards" :key="c.key" class="advice-card" :class="c.cls">
        <div class="advice-head">
          <div class="advice-title">{{ c.title }}</div>
          <button
            class="speaker-btn"
            :class="{
              speaking: activeKey === c.key && isSpeaking,
              loading: activeKey === c.key && isLoading,
            }"
            :title="activeKey === c.key && isLoading ? '加载中...' : activeKey === c.key && isSpeaking ? '停止朗读' : '朗读建议'"
            :disabled="activeKey === c.key && isLoading"
            @click.stop="toggleSpeak(c.key, c.text)"
          >
            <!-- loading 圆圈 -->
            <svg v-if="activeKey === c.key && isLoading" class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-linecap="round" />
            </svg>
            <!-- 喇叭图标 -->
            <svg v-else class="speaker-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <path v-if="activeKey !== c.key || !isSpeaking" d="M15.54 8.46a5 5 0 0 1 0 7.07" />
              <path v-if="activeKey !== c.key || !isSpeaking" d="M19.07 4.93a10 10 0 0 1 0 14.14" />
              <line v-if="activeKey === c.key && isSpeaking" x1="15" y1="8" x2="15" y2="16" />
            </svg>
          </button>
        </div>
        <p class="advice-text">{{ c.text }}</p>
        <button class="advice-btn" disabled>{{ c.btn }}</button>
      </div>
    </div>
    <Transition name="toast">
      <div v-if="errorMsg" class="tts-error-toast">{{ errorMsg }}</div>
    </Transition>
  </SectionCard>
</template>

<style scoped>
.advice-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.advice-card {
  border-radius: 14px;
  padding: 16px 16px 18px;
  display: flex;
  flex-direction: column;
}
.advice-head {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 10px;
}
.speaker-btn {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  color: #999;
  transition: color 0.2s, background 0.2s;
}
.speaker-btn:hover {
  color: #666;
  background: rgba(0,0,0,0.05);
}
.speaker-btn.speaking {
  color: currentColor;
}
.green .speaker-btn.speaking {
  color: #2c9069;
}
.purple .speaker-btn.speaking {
  color: #6a5ad8;
}
.orange .speaker-btn.speaking {
  color: #e08a2b;
}
.spinner {
  width: 18px;
  height: 18px;
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  100% { transform: rotate(360deg); }
}
.speaker-icon {
  width: 18px;
  height: 18px;
}
.speaker-btn.speaking .speaker-icon {
  animation: speaker-wobble 0.5s ease-in-out infinite;
}
@keyframes speaker-wobble {
  0%, 100% { transform: rotate(0deg) scale(1); }
  25% { transform: rotate(-18deg) scale(1.1); }
  75% { transform: rotate(18deg) scale(1.1); }
}
.advice-card.green {
  background: #eef9f3;
}
.advice-card.purple {
  background: #f0eefb;
}
.advice-card.orange {
  background: #fdf3e9;
}
.advice-title {
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 0;
}
.green .advice-title {
  color: #2c9069;
}
.purple .advice-title {
  color: #6a5ad8;
}
.orange .advice-title {
  color: #e08a2b;
}
.advice-text {
  flex: 1;
  margin: 0 0 14px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--c-text-secondary);
}
.advice-btn {
  align-self: center;
  border: none;
  border-radius: 16px;
  padding: 7px 18px;
  font-size: 12px;
  cursor: not-allowed;
  background: #fff;
}
.green .advice-btn {
  color: #2c9069;
}
.purple .advice-btn {
  color: #6a5ad8;
}
.orange .advice-btn {
  color: #e08a2b;
}

/* TTS 错误提示 */
.tts-error-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(239, 68, 68, 0.92);
  color: #fff;
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  z-index: 9999;
  white-space: nowrap;
}
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}
</style>
