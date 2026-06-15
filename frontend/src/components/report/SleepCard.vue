<script setup lang="ts">
// 睡眠监测：ECharts 评分环 + 浅睡/深睡分时堆叠柱
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import type { SleepPanel } from '@/api/types'
import SectionCard from './SectionCard.vue'
import EChart from '@/components/common/EChart.vue'

const props = defineProps<{ sleep: SleepPanel | null }>()

const score = computed(() => props.sleep?.score ?? 0)
const scoreLabel = computed(() => {
  const s = score.value
  return s >= 85 ? '优秀' : s >= 70 ? '良好' : s >= 50 ? '一般' : '欠佳'
})

const gaugeOption = computed<EChartsOption>(() => ({
  series: [
    {
      type: 'gauge',
      startAngle: 90,
      endAngle: -270,
      radius: '92%',
      pointer: { show: false },
      progress: {
        show: true,
        width: 12,
        roundCap: true,
        itemStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 1, y2: 1,
            colorStops: [
              { offset: 0, color: '#5b9bf3' },
              { offset: 1, color: '#3fbf8f' },
            ],
          },
        },
      },
      axisLine: { lineStyle: { width: 12, color: [[1, '#eef3f1']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      anchor: { show: false },
      title: { show: true, offsetCenter: [0, '-32%'], fontSize: 11, color: '#9aa8a2' },
      detail: {
        offsetCenter: [0, '4%'],
        formatter: [`{a|${score.value}}`, `{b|${scoreLabel.value}}`].join('\n'),
        rich: {
          a: { fontSize: 30, fontWeight: 'bolder', color: '#1f2d28', lineHeight: 32 },
          b: { fontSize: 12, color: '#34a87c', lineHeight: 18 },
        },
      },
      data: [{ value: score.value, name: '睡眠评分' }],
    },
  ],
}))

const barOption = computed<EChartsOption>(() => {
  const tl = props.sleep?.stages_timeline ?? []
  const hours = tl.map((s) => s.hour)
  const light = tl.map((s) => s.light || 0)
  const deep = tl.map((s) => s.deep || 0)
  return {
    grid: { left: 4, right: 4, top: 8, bottom: 4, containLabel: true },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category', data: hours, axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e6efea' } },
      axisLabel: { color: '#9aa8a2', fontSize: 10 },
    },
    yAxis: { type: 'value', show: false },
    series: [
      { name: '浅睡', type: 'bar', stack: 's', data: light, barWidth: '55%', itemStyle: { color: '#b9c6f7' } },
      { name: '深睡', type: 'bar', stack: 's', data: deep, itemStyle: { color: '#6a73d8', borderRadius: [3, 3, 0, 0] } },
    ],
  }
})
</script>

<template>
  <SectionCard title="睡眠监测" more>
    <div class="ring-wrap">
      <EChart :option="gaugeOption" height="150px" />
    </div>

    <div class="legend">
      <span class="dot light" /> 浅睡
      <span class="dot deep" /> 深睡
    </div>

    <div v-if="(sleep?.stages_timeline?.length ?? 0)">
      <EChart :option="barOption" height="120px" />
    </div>
    <div v-else class="bars-empty">暂无睡眠分时数据</div>
  </SectionCard>
</template>

<style scoped>
.ring-wrap {
  width: 100%;
}
.legend {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  font-size: 12px;
  color: var(--c-text-secondary);
  margin: 8px 0 6px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  display: inline-block;
}
.dot.light {
  background: #b9c6f7;
}
.dot.deep {
  background: #6a73d8;
}
.dot + .dot {
  margin-left: 10px;
}
.bars-empty {
  padding: 36px 0;
  text-align: center;
  font-size: 12px;
  color: var(--c-text-tertiary);
}
</style>
