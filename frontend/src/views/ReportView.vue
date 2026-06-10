<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useReportStore } from '@/stores/report'
import ReportHeader from '@/components/report/ReportHeader.vue'
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
      <ReportHeader />

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
  overflow-y: auto;
  padding-right: 6px;
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
}
</style>
