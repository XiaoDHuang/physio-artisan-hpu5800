<script setup lang="ts">
// 今日运动建议：运动 / 饮食 / 睡眠 三段建议 + 查看详情
import { computed } from 'vue'
import type { ExerciseAdvice } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import iconExercise from '@/assets/page-exercise/运动建议.png'
import iconDiet from '@/assets/page-exercise/饮食建议.png'
import iconSleep from '@/assets/page-exercise/睡眠建议.png'

const props = defineProps<{ advice: ExerciseAdvice | null }>()

const sections = computed(() => [
  { key: 'exercise', icon: iconExercise, title: '运动建议', text: props.advice?.exercise || '—' },
  { key: 'nutrition', icon: iconDiet, title: '饮食建议', text: props.advice?.nutrition || '—' },
  { key: 'sleep', icon: iconSleep, title: '睡眠建议', text: props.advice?.sleep || '—' },
])
</script>

<template>
  <SectionCard title="今日运动建议">
    <div class="hint">根据你的饮食、睡眠和运动数据，我们推荐以下建议：</div>
    <div v-for="s in sections" :key="s.key" class="sec">
      <div class="sec-head">
        <img :src="s.icon" class="sec-icon" alt="" />
        <span class="sec-title">{{ s.title }}</span>
      </div>
      <p class="sec-text">{{ s.text }}</p>
    </div>
    <button class="more-btn" type="button">查看详情</button>
  </SectionCard>
</template>

<style scoped>
.hint {
  font-size: 12px;
  color: var(--c-text-tertiary);
  margin-bottom: 12px;
}
.sec {
  margin-bottom: 14px;
}
.sec-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.sec-icon {
  width: 22px;
  height: 22px;
  object-fit: contain;
}
.sec-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
}
.sec-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--c-text-secondary);
}
.more-btn {
  width: 100%;
  margin-top: 6px;
  border: none;
  background: var(--c-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  padding: 10px 0;
  border-radius: 22px;
  cursor: pointer;
}
.more-btn:hover {
  background: var(--c-primary-hover);
}
</style>
