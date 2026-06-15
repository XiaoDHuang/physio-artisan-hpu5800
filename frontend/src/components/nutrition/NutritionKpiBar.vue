<script setup lang="ts">
// 顶部：日期切换 + 每日目标 / 已摄入 / 还可摄入 / 达成率 四卡
import { computed } from 'vue'
import type { NutritionKpi } from '@/api/types'
import icGoal from '@/assets/page-nutrition/每日目标.png'
import icIntake from '@/assets/page-nutrition/已攝入.png'
import icRemain from '@/assets/page-nutrition/还可攝入‘.png'
import icRate from '@/assets/page-nutrition/达成率.png'

const props = defineProps<{ kpi: NutritionKpi | null; date: string }>()
const emit = defineEmits<{ (e: 'prev'): void; (e: 'next'): void }>()

const dash = (v: number | null | undefined) => (v == null ? '—' : v)

const cards = computed(() => {
  const k = props.kpi
  return [
    { key: 'goal', icon: icGoal, label: '每日目标', value: dash(k?.goal_calories), unit: '千卡' },
    { key: 'intake', icon: icIntake, label: '已摄入', value: dash(k?.intake_calories), unit: '千卡' },
    { key: 'remain', icon: icRemain, label: '还可摄入', value: dash(k?.remaining_calories), unit: '千卡' },
    { key: 'rate', icon: icRate, label: '达成率', value: dash(k?.achievement_rate), unit: '%' },
  ]
})
</script>

<template>
  <div class="kpi-bar">
    <div class="date-card">
      <button class="nav" @click="emit('prev')">‹</button>
      <div class="date">
        <span class="cal-ico">📅</span>
        {{ date || '—' }}
      </div>
      <button class="nav" @click="emit('next')">›</button>
    </div>

    <div v-for="c in cards" :key="c.key" class="kpi-card">
      <img :src="c.icon" class="kpi-icon" alt="" />
      <div class="kpi-content">
        <div class="kpi-label">{{ c.label }}</div>
        <div class="kpi-value">{{ c.value }}<span class="kpi-unit">{{ c.unit }}</span></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpi-bar {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr 1fr 1fr;
  gap: 14px;
}
.date-card,
.kpi-card {
  background: var(--c-card-bg);
  border-radius: 14px;
  box-shadow: 0 4px 16px rgba(31, 45, 40, 0.06);
  min-height: 78px;
}
.date-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
}
.nav {
  width: 30px;
  height: 30px;
  border: none;
  background: #f3f5f7;
  border-radius: 8px;
  font-size: 18px;
  color: var(--c-text-secondary);
  cursor: pointer;
}
.nav:hover {
  background: var(--c-primary-soft);
  color: var(--c-primary-hover);
}
.date {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: var(--c-text);
}
.cal-ico {
  font-size: 14px;
}
.kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
}
.kpi-icon {
  width: 40px;
  height: 40px;
  object-fit: contain;
  flex-shrink: 0;
}
.kpi-label {
  font-size: 13px;
  color: var(--c-text-secondary);
}
.kpi-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--c-text);
  line-height: 1.2;
  margin-top: 2px;
}
.kpi-unit {
  font-size: 12px;
  font-weight: 500;
  color: var(--c-text-tertiary);
  margin-left: 3px;
}
</style>
