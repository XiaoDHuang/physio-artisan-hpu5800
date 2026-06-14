<script setup lang="ts">
// 今日睡眠概况：ECharts 环形评分 + 等级文案
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'
import type { SleepToday } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import EChart from '@/components/common/EChart.vue'
import bannerBg from '@/assets/page-sleep/banner-bg.png'

const props = defineProps<{ today: SleepToday | null }>()

// 背景：睡觉插画靠右 + 左侧浅色渐变（评分环/文案落在左侧白底）
const bodyStyle = {
  backgroundImage: `url(${bannerBg}), linear-gradient(110deg, #f3f8ff 0%, #eef9f4 55%, #ffffff 100%)`,
  backgroundRepeat: 'no-repeat, no-repeat',
  backgroundPosition: 'right center, center',
  backgroundSize: 'auto 100%, cover',
}

const GRADE_MSG: Record<string, string> = {
  优秀: '睡眠质量优秀，继续保持这份好状态！',
  良好: '睡眠质量良好，继续保持规律作息！',
  一般: '睡眠质量一般，建议规律作息、睡前放松。',
  较差: '睡眠质量欠佳，注意减少熬夜与咖啡因摄入。',
}
const message = computed(() => GRADE_MSG[props.today?.grade || ''] || '记录睡眠时间，获取更准确的睡眠分析。')

const option = computed<EChartsOption>(() => {
  const score = props.today?.sleep_score ?? 0
  const grade = props.today?.grade || '—'
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 90,
        endAngle: -270,
        radius: '92%',
        pointer: { show: false },
        progress: {
          show: true,
          width: 14,
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
        axisLine: { lineStyle: { width: 14, color: [[1, '#eef3f1']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        anchor: { show: false },
        title: { show: true, offsetCenter: [0, '-34%'], fontSize: 12, color: '#9aa8a2' },
        detail: {
          offsetCenter: [0, '6%'],
          formatter: [`{a|${score}}`, `{b|${grade}}`].join('\n'),
          rich: {
            a: { fontSize: 36, fontWeight: 'bolder', color: '#1f2d28', lineHeight: 40 },
            b: { fontSize: 13, color: '#34a87c', lineHeight: 20 },
          },
        },
        data: [{ value: score, name: '睡眠评分' }],
      },
    ],
  }
})
</script>

<template>
  <SectionCard title="今日睡眠概况">
    <div class="body" :style="bodyStyle">
      <div class="left">
        <div class="ring">
          <EChart :option="option" height="190px" />
        </div>
        <div class="message">{{ message }}</div>
      </div>
    </div>
  </SectionCard>
</template>

<style scoped>
.body {
  display: flex;
  align-items: center;
  border-radius: 14px;
  padding: 14px 24px;
  min-height: 210px;
}
.left {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 240px;
  flex-shrink: 0;
}
.ring {
  width: 190px;
}
.message {
  margin-top: 2px;
  max-width: 230px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-secondary);
  line-height: 1.6;
}
</style>
