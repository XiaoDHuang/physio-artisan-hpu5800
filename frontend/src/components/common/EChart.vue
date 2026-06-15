<script setup lang="ts">
// ECharts 薄封装：集中按需注册（树摇）+ 统一 autoresize。
// 各图表组件只产出 option，不各自 import echarts。
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, GaugeChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import type { EChartsOption } from 'echarts'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  GaugeChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
])

defineProps<{ option: EChartsOption; height?: string }>()
</script>

<template>
  <v-chart class="echart" :option="option" autoresize :style="{ height: height || '240px' }" />
</template>

<style scoped>
.echart {
  width: 100%;
}
</style>
