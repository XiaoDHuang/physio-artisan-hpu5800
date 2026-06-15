<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useReportStore } from '@/stores/report'
import AppHeader from '@/components/common/AppHeader.vue'
import KpiCards from '@/components/report/KpiCards.vue'
import BodyOverview from '@/components/report/BodyOverview.vue'
import SectionCard from '@/components/report/SectionCard.vue'
import HealthAdviceCard from '@/components/report/HealthAdviceCard.vue'
import SleepCard from '@/components/report/SleepCard.vue'
import NutritionCard from '@/components/report/NutritionCard.vue'
import ExerciseCard from '@/components/report/ExerciseCard.vue'
import ChatDock from '@/components/report/ChatDock.vue'

const store = useReportStore()
const { kpi, body, sleep, nutrition, exerciseToday, weekSummary, healthAdvice } = storeToRefs(store)

onMounted(() => {
  store.load()
})
</script>

<template>
  <div class="report-view">
    <div class="scroll-area">
      <div class="report-content">
      <AppHeader title="健康报告" subtitle="基于您的运动、睡眠、饮食等数据综合分析">
        <span class="hdr-pill">2026-06-01健康数据</span>
        <span class="hdr-pill hdr-date">
          <svg class="hdr-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          2026 - 06 - 01
        </span>
        <button class="hdr-export">
          <svg class="hdr-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          导出报告
        </button>
      </AppHeader>

      <!-- 顶部 4 KPI -->
      <KpiCards :kpi="kpi" />

      <!-- 主体两栏：左宽(身体概览+健康建议) / 右窄(睡眠/饮食/运动) -->
      <div class="grid">
        <div class="col-left">
          <SectionCard title="身体指标概览">
            <BodyOverview :body="body" />
          </SectionCard>
          <HealthAdviceCard :advice="healthAdvice" />
        </div>

        <div class="col-right">
          <SleepCard :sleep="sleep" />
          <NutritionCard :nutrition="nutrition" />
          <ExerciseCard :exercise="exerciseToday" :week="weekSummary" />
        </div>
      </div>

      <!-- 底部聊天卡片（整宽）-->
      <ChatDock />
      </div>
    </div>
  </div>
</template>

<style scoped>
.report-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 22px 28px 16px;
}
.scroll-area {
  flex: 1;
  overflow: auto;
  padding-right: 6px;
}
.report-content {
  min-width: 1120px;
}
.grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 16px;
  align-items: start;
}
.col-left,
.col-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

/* Header 中间槽：健康数据标签 / 日期 / 导出报告 */
.hdr-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 14px;
  background: #f3f5f7;
  border-radius: 8px;
  font-size: 13px;
  color: #5f6b66;
  white-space: nowrap;
}
.hdr-date {
  color: #3d3d3d;
}
.hdr-export {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 16px;
  border: none;
  border-radius: 8px;
  background: var(--c-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.hdr-export:hover {
  background: var(--c-primary-hover);
}
.hdr-ico {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}
</style>
