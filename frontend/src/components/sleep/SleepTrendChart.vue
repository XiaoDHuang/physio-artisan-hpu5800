<script setup lang="ts">
// 睡眠趋势：睡眠时长(柱) + 睡眠评分(线) 双轴；近 7/14 天切换
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import type { SleepTrendPoint } from '@/api/types'
import type { SleepRangeOpt } from '@/api/sleep'
import SectionCard from '@/components/report/SectionCard.vue'
import EChart from '@/components/common/EChart.vue'

const props = defineProps<{ trend: SleepTrendPoint[]; range: SleepRangeOpt }>()
const emit = defineEmits<{ (e: 'change-range', v: SleepRangeOpt): void }>()

function mmdd(d: string): string {
  const p = d.split('-')
  return p.length === 3 ? `${Number(p[1])}/${Number(p[2])}` : d
}

const option = computed<EChartsOption>(() => {
  const days = props.trend.map((t) => mmdd(t.date))
  const hours = props.trend.map((t) => t.total_hours ?? 0)
  const scores = props.trend.map((t) => t.sleep_score ?? 0)
  return {
    grid: { left: 8, right: 8, top: 40, bottom: 8, containLabel: true },
    tooltip: { trigger: 'axis' },
    legend: { data: ['睡眠时长(小时)', '睡眠评分(分)'], top: 0, icon: 'roundRect', itemWidth: 14, itemHeight: 8, textStyle: { fontSize: 12, color: '#6b7d76' } },
    xAxis: {
      type: 'category', data: days, axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e6efea' } },
      axisLabel: { color: '#9aa8a2', fontSize: 11 },
    },
    yAxis: [
      { type: 'value', min: 0, max: 12, splitLine: { lineStyle: { color: '#f0f4f2' } }, axisLabel: { color: '#9aa8a2', fontSize: 11 } },
      { type: 'value', min: 0, max: 100, splitLine: { show: false }, axisLabel: { color: '#9aa8a2', fontSize: 11 } },
    ],
    series: [
      { name: '睡眠时长(小时)', type: 'bar', yAxisIndex: 0, data: hours, barWidth: '42%',
        itemStyle: { color: '#a9b6f0', borderRadius: [4, 4, 0, 0] } },
      { name: '睡眠评分(分)', type: 'line', yAxisIndex: 1, data: scores, smooth: true, symbol: 'circle', symbolSize: 7,
        lineStyle: { color: '#7b6ed6', width: 2 }, itemStyle: { color: '#7b6ed6' } },
    ],
  }
})
</script>

<template>
  <SectionCard>
    <div class="head">
      <span class="title">睡眠趋势</span>
      <a-select
        :value="range"
        size="small"
        style="width: 96px"
        :options="[
          { value: '7d', label: '近7天' },
          { value: '14d', label: '近14天' },
        ]"
        @change="(v: SleepRangeOpt) => emit('change-range', v)"
      />
    </div>
    <EChart v-if="trend.length" :option="option" height="260px" />
    <div v-else class="empty">暂无趋势数据</div>
  </SectionCard>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.title {
  font-size: 16px;
  font-weight: 700;
  color: var(--c-text);
}
.empty {
  padding: 48px 0;
  text-align: center;
  font-size: 13px;
  color: var(--c-text-tertiary);
}
</style>
