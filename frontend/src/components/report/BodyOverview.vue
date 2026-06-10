<script setup lang="ts">
import { computed } from 'vue'
import type { BodyOverview } from '@/api/types'
import bg from '@/assets/physical-indicators-overview/physical-indicators-overview-bg.png'
import iconHr from '@/assets/physical-indicators-overview/心率.png'
import iconWeight from '@/assets/physical-indicators-overview/体重.png'
import iconBmi from '@/assets/physical-indicators-overview/BMI.png'
import iconBmr from '@/assets/physical-indicators-overview/基础代谢.png'
import iconFat from '@/assets/physical-indicators-overview/体脂率.png'
import iconMuscle from '@/assets/physical-indicators-overview/肌肉量.png'

const props = defineProps<{ body: BodyOverview | null }>()

const d = (v: number | null | undefined) => (v === null || v === undefined ? '—' : v)

const left = computed(() => {
  const b = props.body
  return [
    { icon: iconHr, label: '心率', value: d(b?.heart_rate), unit: '次/分' },
    { icon: iconBmi, label: 'BMI', value: d(b?.bmi), unit: '' },
    { icon: iconFat, label: '体脂率', value: d(b?.body_fat_pct), unit: '%' },
  ]
})
const right = computed(() => {
  const b = props.body
  return [
    { icon: iconWeight, label: '体重', value: d(b?.weight_kg), unit: 'kg' },
    { icon: iconBmr, label: '基础代谢', value: d(b?.bmr), unit: '千卡' },
    { icon: iconMuscle, label: '肌肉量', value: d(b?.muscle_mass_kg), unit: 'kg' },
  ]
})
const updateDate = computed(() => props.body?.update_date || '—')
</script>

<template>
  <div class="body-overview">
    <div class="metric-col">
      <div v-for="m in left" :key="m.label" class="metric metric-left">
        <img :src="m.icon" class="metric-icon" alt="" />
        <div class="metric-text">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value">{{ m.value }}<span class="metric-unit">{{ m.unit }}</span></div>
        </div>
      </div>
    </div>

    <div class="body-center">
      <img :src="bg" class="body-img" alt="身体指标" />
    </div>

    <div class="metric-col">
      <div v-for="m in right" :key="m.label" class="metric metric-right">
        <img :src="m.icon" class="metric-icon" alt="" />
        <div class="metric-text">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value">{{ m.value }}<span class="metric-unit">{{ m.unit }}</span></div>
        </div>
      </div>
    </div>

    <div class="source-line">数据来源：智能手环、体脂秤、适动APP ｜ 更新时间：{{ updateDate }}</div>
  </div>
</template>

<style scoped>
.body-overview {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  padding: 8px 4px 30px;
  min-height: 360px;
}
.metric-col {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 34px;
}
.metric {
  display: flex;
  align-items: center;
  gap: 12px;
}
.metric-right {
  flex-direction: row-reverse;
  text-align: right;
}
.metric-icon {
  width: 40px;
  height: 40px;
  object-fit: contain;
}
.metric-label {
  font-size: 13px;
  color: var(--c-text-secondary);
}
.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--c-text);
}
.metric-unit {
  font-size: 12px;
  font-weight: 500;
  color: var(--c-text-tertiary);
  margin-left: 3px;
}
.body-center {
  display: flex;
  justify-content: center;
}
.body-img {
  height: 320px;
  object-fit: contain;
}
.source-line {
  position: absolute;
  bottom: 4px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 12px;
  color: var(--c-text-tertiary);
}
</style>
