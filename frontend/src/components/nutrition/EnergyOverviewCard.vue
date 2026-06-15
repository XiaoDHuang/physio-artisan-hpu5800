<script setup lang="ts">
// 能量摄入概览：环形(宏量占比) + 宏量条 + 右侧推荐/BMR/运动消耗/能量缺口 + 温馨提示
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import type { NutritionEnergy } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import EChart from '@/components/common/EChart.vue'
import icCenter from '@/assets/page-nutrition/已攝入总能量.png'
import icRecommend from '@/assets/page-nutrition/推荐摄入.png'
import icBmr from '@/assets/page-nutrition/基础代谢.png'
import icBurn from '@/assets/page-nutrition/运动消耗.png'
import icGap from '@/assets/page-nutrition/能量缺口.png'
import icTip from '@/assets/page-nutrition/温馨提示.png'

const props = defineProps<{ energy: NutritionEnergy | null }>()

const dash = (v: number | null | undefined) => (v == null ? '—' : v)

const COLORS = { carbs: '#9b8cf5', protein: '#f5c24b', fat: '#5fb98f' }

const macros = computed(() => {
  const m = props.energy?.macros
  return [
    { key: 'carbs', name: '碳水化合物', color: COLORS.carbs, item: m?.carbs },
    { key: 'protein', name: '蛋白质', color: COLORS.protein, item: m?.protein },
    { key: 'fat', name: '脂肪', color: COLORS.fat, item: m?.fat },
  ]
})

const option = computed<EChartsOption>(() => {
  const m = props.energy?.macros
  return {
    series: [
      {
        type: 'pie',
        radius: ['64%', '88%'],
        avoidLabelOverlap: false,
        silent: true,
        label: { show: false },
        data: [
          { value: m?.carbs.calories ?? 0, name: '碳水', itemStyle: { color: COLORS.carbs } },
          { value: m?.protein.calories ?? 0, name: '蛋白质', itemStyle: { color: COLORS.protein } },
          { value: m?.fat.calories ?? 0, name: '脂肪', itemStyle: { color: COLORS.fat } },
        ],
      },
    ],
  }
})

const metrics = computed(() => {
  const e = props.energy
  return [
    { key: 'rec', icon: icRecommend, label: '推荐摄入', value: dash(e?.recommended_calories) },
    { key: 'bmr', icon: icBmr, label: '基础代谢', value: dash(e?.bmr) },
    { key: 'burn', icon: icBurn, label: '运动消耗', value: dash(e?.exercise_burn) },
    { key: 'gap', icon: icGap, label: '能量缺口', value: dash(e?.energy_gap) },
  ]
})
</script>

<template>
  <SectionCard title="能量摄入概览">
    <div class="grid">
      <div class="donut">
        <EChart :option="option" height="200px" />
        <div class="center">
          <img :src="icCenter" class="center-ic" alt="" />
          <div class="center-cal">{{ dash(energy?.total_calories) }}<span>千卡</span></div>
          <div class="center-label">已摄入总能量</div>
        </div>
      </div>

      <div class="macros">
        <div v-for="mm in macros" :key="mm.key" class="macro">
          <div class="macro-top">
            <span class="dot" :style="{ background: mm.color }" />
            <span class="macro-name">{{ mm.name }}</span>
            <span class="macro-val">
              {{ dash(mm.item?.grams) }}g / {{ dash(mm.item?.calories) }} 千卡
            </span>
          </div>
          <div class="macro-bar">
            <div class="macro-fill" :style="{ width: (mm.item?.percent ?? 0) + '%', background: mm.color }" />
          </div>
        </div>
      </div>

      <div class="metrics">
        <div v-for="mt in metrics" :key="mt.key" class="metric">
          <img :src="mt.icon" class="metric-ic" alt="" />
          <span class="metric-label">{{ mt.label }}</span>
          <span class="metric-value">{{ mt.value }} <span class="u">千卡</span></span>
        </div>
      </div>
    </div>

    <div class="tip">
      <img :src="icTip" class="tip-ic" alt="" />
      温馨提示：保持均衡饮食，合理搭配碳水、蛋白质和脂肪，有助于达成健身目标。
    </div>
  </SectionCard>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 220px 1fr 220px;
  gap: 24px;
  align-items: center;
}
.donut {
  position: relative;
  width: 220px;
  height: 200px;
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
.center-ic {
  width: 26px;
  height: 26px;
  object-fit: contain;
  margin-bottom: 2px;
}
.center-cal {
  font-size: 26px;
  font-weight: 800;
  color: var(--c-text);
}
.center-cal span {
  font-size: 12px;
  font-weight: 500;
  color: var(--c-text-tertiary);
  margin-left: 2px;
}
.center-label {
  font-size: 12px;
  color: var(--c-text-tertiary);
}
.macros {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.macro-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.macro-name {
  font-size: 13px;
  color: var(--c-text-secondary);
}
.macro-val {
  margin-left: auto;
  font-size: 13px;
  color: var(--c-text);
  font-weight: 600;
}
.macro-bar {
  height: 7px;
  border-radius: 4px;
  background: #eef3f1;
  overflow: hidden;
}
.macro-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.metrics {
  display: flex;
  flex-direction: column;
  gap: 14px;
  border-left: 1px solid var(--c-border);
  padding-left: 22px;
}
.metric {
  display: flex;
  align-items: center;
  gap: 10px;
}
.metric-ic {
  width: 30px;
  height: 30px;
  object-fit: contain;
}
.metric-label {
  font-size: 13px;
  color: var(--c-text-secondary);
}
.metric-value {
  margin-left: auto;
  font-size: 15px;
  font-weight: 700;
  color: var(--c-text);
}
.metric-value .u {
  font-size: 11px;
  font-weight: 400;
  color: var(--c-text-tertiary);
}
.tip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  background: var(--c-primary-soft);
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 13px;
  color: var(--c-text-secondary);
}
.tip-ic {
  width: 18px;
  height: 18px;
  object-fit: contain;
  flex-shrink: 0;
}
</style>
