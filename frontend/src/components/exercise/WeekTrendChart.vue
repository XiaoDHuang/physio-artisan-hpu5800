<script setup lang="ts">
// 本周运动趋势：步数柱状 + 目标线（ECharts）
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import type { WeekTrendPoint } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import EChart from '@/components/common/EChart.vue'

const props = defineProps<{ trend: WeekTrendPoint[]; goal: number | null }>()

function mmdd(d: string): string {
  const p = d.split('-')
  return p.length === 3 ? `${Number(p[1])}/${Number(p[2])}` : d
}

const option = computed<EChartsOption>(() => {
  const days = props.trend.map((t) => mmdd(t.date))
  const steps = props.trend.map((t) => t.steps ?? 0)
  const lastIdx = steps.length - 1
  return {
    grid: { left: 8, right: 12, top: 24, bottom: 8, containLabel: true },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: days,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e6efea' } },
      axisLabel: { color: '#9aa8a2', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f0f4f2' } },
      axisLabel: { color: '#9aa8a2', fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        data: steps.map((v, i) => ({
          value: v,
          itemStyle: { color: i === lastIdx ? '#34a87c' : '#a9e3cd', borderRadius: [4, 4, 0, 0] },
        })),
        barWidth: '46%',
        markLine: props.goal
          ? {
              symbol: 'none',
              data: [{ yAxis: props.goal }],
              lineStyle: { color: '#3fbf8f', type: 'dashed' },
              label: { formatter: `目标 ${props.goal} 步`, color: '#34a87c', fontSize: 11, position: 'insideEndTop' },
            }
          : undefined,
      },
    ],
  }
})
</script>

<template>
  <SectionCard title="本周运动趋势">
    <EChart v-if="trend.length" :option="option" height="240px" />
    <div v-else class="empty">暂无趋势数据</div>
  </SectionCard>
</template>

<style scoped>
.empty {
  padding: 40px 0;
  text-align: center;
  font-size: 13px;
  color: var(--c-text-tertiary);
}
</style>
