<script setup lang="ts">
import { computed } from 'vue'
import type { HealthAdvice } from '@/api/types'
import SectionCard from './SectionCard.vue'

const props = defineProps<{ advice: HealthAdvice | null }>()

// 占位文案（无报告时显示）
const PLACEHOLDER = {
  exercise: '每日 30 分钟有氧搭配 15 分钟力量，快走、哑铃皆可。足量饮水，循序渐进加量，助力提升肌肉、优化体脂。',
  sleep: '固定 23 点前入睡，每日睡 7–8 小时，睡前少看电子屏、忌浓茶咖啡。卧室避光恒温，规律作息稳代谢。',
  nutrition: '三餐粗细搭配，优质蛋白足量摄入，少油少盐控糖。多吃蔬菜，主食替换杂粮，规律进餐稳血糖。',
}

const cards = computed(() => [
  { key: 'exercise', title: '运动建议', cls: 'green', text: props.advice?.exercise || PLACEHOLDER.exercise, btn: '查看运动计划' },
  { key: 'sleep', title: '睡眠建议', cls: 'purple', text: props.advice?.sleep || PLACEHOLDER.sleep, btn: '查看改善方法' },
  { key: 'nutrition', title: '饮食建议', cls: 'orange', text: props.advice?.nutrition || PLACEHOLDER.nutrition, btn: '查看饮食方案' },
])
</script>

<template>
  <SectionCard title="健康建议">
    <div class="advice-grid">
      <div v-for="c in cards" :key="c.key" class="advice-card" :class="c.cls">
        <div class="advice-title">{{ c.title }}</div>
        <p class="advice-text">{{ c.text }}</p>
        <button class="advice-btn" disabled>{{ c.btn }}</button>
      </div>
    </div>
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
  margin-bottom: 10px;
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
</style>
