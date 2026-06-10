<script setup lang="ts">
import { computed } from 'vue'
import type { NutritionPanel } from '@/api/types'
import SectionCard from './SectionCard.vue'

const props = defineProps<{ nutrition: NutritionPanel | null }>()

const COLORS = { carbs: '#7c6cf0', protein: '#f5b945', fat: '#3fbf8f', other: '#ef6b6b' }

const total = computed(() => props.nutrition?.total_calories ?? null)

const segs = computed(() => {
  const r = props.nutrition?.ratios ?? {}
  const carbs = r.carbs ?? 0
  const protein = r.protein ?? 0
  const fat = r.fat ?? 0
  const other = Math.max(0, 100 - carbs - protein - fat)
  return [
    { key: 'carbs', label: '碳水化合物', val: carbs, color: COLORS.carbs },
    { key: 'protein', label: '蛋白质', val: protein, color: COLORS.protein },
    { key: 'fat', label: '脂肪', val: fat, color: COLORS.fat },
    { key: 'other', label: '其他', val: other, color: COLORS.other },
  ]
})

const donutStyle = computed(() => {
  let acc = 0
  const stops = segs.value
    .map((s) => {
      const from = acc
      acc += s.val
      return `${s.color} ${from}% ${acc}%`
    })
    .join(', ')
  return { background: `conic-gradient(${stops})` }
})

const balance = computed(() => props.nutrition?.balance_score ?? null)
const balanceLabel = computed(() => {
  const b = balance.value ?? 0
  return b >= 80 ? '良好' : b >= 60 ? '一般' : '待改善'
})
</script>

<template>
  <SectionCard title="饮食监测" more>
    <div class="nutri-body">
      <div class="donut" :style="donutStyle">
        <div class="donut-inner">
          <div class="kcal">{{ total ?? '—' }}<span class="unit">千卡</span></div>
          <div class="kcal-label">总摄入</div>
        </div>
      </div>
      <ul class="legend">
        <li v-for="s in segs" :key="s.key">
          <span class="dot" :style="{ background: s.color }" />{{ s.label }}
        </li>
      </ul>
    </div>

    <div class="balance">
      <span class="bal-label">饮食均衡度</span>
      <div class="bal-track"><div class="bal-fill" :style="{ width: (balance ?? 0) + '%' }" /></div>
      <span class="bal-tag">{{ balanceLabel }}</span>
    </div>
  </SectionCard>
</template>

<style scoped>
.nutri-body {
  display: flex;
  align-items: center;
  gap: 22px;
}
.donut {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.donut-inner {
  width: 74px;
  height: 74px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.kcal {
  font-size: 18px;
  font-weight: 800;
  color: var(--c-text);
}
.unit {
  font-size: 11px;
  font-weight: 500;
  color: var(--c-text-tertiary);
  margin-left: 2px;
}
.kcal-label {
  font-size: 11px;
  color: var(--c-text-tertiary);
}
.legend {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 14px;
}
.legend li {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--c-text-secondary);
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  display: inline-block;
}
.balance {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 18px;
}
.bal-label {
  font-size: 13px;
  color: var(--c-text-secondary);
  white-space: nowrap;
}
.bal-track {
  flex: 1;
  height: 8px;
  background: #eef3f1;
  border-radius: 4px;
  overflow: hidden;
}
.bal-fill {
  height: 100%;
  background: linear-gradient(90deg, #7cd9b3, var(--c-primary));
  border-radius: 4px;
}
.bal-tag {
  font-size: 12px;
  color: var(--c-primary-hover);
  border: 1px solid var(--c-primary);
  border-radius: 10px;
  padding: 1px 10px;
}
</style>
