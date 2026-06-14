<script setup lang="ts">
// 饮食监测：ECharts 环形(宏量占比) + 右侧图例 + 饮食均衡度
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import type { NutritionPanel } from '@/api/types'
import SectionCard from './SectionCard.vue'
import EChart from '@/components/common/EChart.vue'

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

const option = computed<EChartsOption>(() => ({
  series: [
    {
      type: 'pie',
      radius: ['62%', '88%'],
      silent: true,
      label: { show: false },
      data: segs.value.map((s) => ({ value: s.val, name: s.label, itemStyle: { color: s.color } })),
    },
  ],
}))

const balance = computed(() => props.nutrition?.balance_score ?? null)
const balanceLabel = computed(() => {
  const b = balance.value ?? 0
  return b >= 80 ? '良好' : b >= 60 ? '一般' : '待改善'
})
</script>

<template>
  <SectionCard title="饮食监测" more>
    <div class="nutri-body">
      <div class="donut">
        <EChart :option="option" height="120px" />
        <div class="center">
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
  gap: 16px;
}
.donut {
  position: relative;
  width: 120px;
  height: 120px;
  flex-shrink: 0;
}
.center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
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
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.legend li {
  display: flex;
  align-items: center;
  gap: 8px;
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
