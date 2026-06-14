<script setup lang="ts">
// 今日运动总览：步数 / 消耗卡里 / 运动时长 / 运动强度 四指标 + 目标进度条
import { computed } from 'vue'
import type { ExerciseTodayOverview } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import iconSteps from '@/assets/page-exercise/步数.png'
import iconCal from '@/assets/page-exercise/消耗卡里.png'
import iconDur from '@/assets/page-exercise/运动时长.png'
import iconInt from '@/assets/page-exercise/运动强度.png'

const props = defineProps<{ overview: ExerciseTodayOverview | null }>()

const dash = (v: number | null | undefined) => (v === null || v === undefined ? '—' : v)

// 运动强度 字符串 → 进度百分比
function intensityPct(label: string): number {
  if (label === '高') return 100
  if (label === '中等') return 66
  if (label === '低') return 33
  return 0
}

const tiles = computed(() => {
  const o = props.overview
  const pct = (v?: number | null, g?: number | null) =>
    v && g ? Math.min(100, Math.round((v / g) * 100)) : 0
  return [
    { key: 'steps', icon: iconSteps, label: '步数', value: dash(o?.steps), unit: '步',
      goal: o?.steps_goal, goalUnit: '步', percent: pct(o?.steps, o?.steps_goal), color: '#3fbf8f' },
    { key: 'cal', icon: iconCal, label: '消耗卡里', value: dash(o?.calories_burned), unit: 'kcal',
      goal: o?.calories_goal, goalUnit: 'kcal', percent: pct(o?.calories_burned, o?.calories_goal), color: '#5b9bf3' },
    { key: 'dur', icon: iconDur, label: '运动时长', value: dash(o?.duration_minutes), unit: '分钟',
      goal: o?.duration_goal, goalUnit: '分钟', percent: pct(o?.duration_minutes, o?.duration_goal), color: '#f5a623' },
    { key: 'int', icon: iconInt, label: '运动强度', value: o?.intensity || '—', unit: '',
      goal: null, goalUnit: '', percent: intensityPct(o?.intensity || ''), color: '#9b8cf5' },
  ]
})
</script>

<template>
  <SectionCard title="今日运动总览">
    <div class="grid">
      <div v-for="t in tiles" :key="t.key" class="tile">
        <img :src="t.icon" class="tile-icon" alt="" />
        <div class="tile-label">{{ t.label }}</div>
        <div class="tile-value">
          {{ t.value }}<span v-if="t.unit" class="tile-unit">{{ t.unit }}</span>
        </div>
        <div class="tile-goal">
          <template v-if="t.goal">目标 {{ t.goal }} {{ t.goalUnit }}</template>
          <template v-else>&nbsp;</template>
        </div>
        <div class="bar">
          <div class="bar-fill" :style="{ width: t.percent + '%', background: t.color }" />
        </div>
      </div>
    </div>
  </SectionCard>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}
.tile {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.tile-icon {
  width: 44px;
  height: 44px;
  object-fit: contain;
  margin-bottom: 10px;
}
.tile-label {
  font-size: 13px;
  color: var(--c-text-secondary);
}
.tile-value {
  font-size: 24px;
  font-weight: 800;
  color: var(--c-text);
  line-height: 1.2;
  margin-top: 2px;
}
.tile-unit {
  font-size: 13px;
  font-weight: 500;
  color: var(--c-text-tertiary);
  margin-left: 3px;
}
.tile-goal {
  font-size: 12px;
  color: var(--c-text-tertiary);
  margin: 6px 0 8px;
}
.bar {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #eef3f1;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}
</style>
