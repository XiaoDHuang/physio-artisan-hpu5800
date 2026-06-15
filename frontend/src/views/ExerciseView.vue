<script setup lang="ts">
// 运动分析页：AppHeader + Banner + 左(总览/记录/趋势) 右(状态/建议) + 成就横幅
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useExerciseStore } from '@/stores/exercise'
import AppHeader from '@/components/common/AppHeader.vue'
import ExerciseBanner from '@/components/exercise/ExerciseBanner.vue'
import TodayOverviewCard from '@/components/exercise/TodayOverviewCard.vue'
import TodayRecordsCard from '@/components/exercise/TodayRecordsCard.vue'
import WeekTrendChart from '@/components/exercise/WeekTrendChart.vue'
import TodayStatusCard from '@/components/exercise/TodayStatusCard.vue'
import ExerciseAdviceCard from '@/components/exercise/ExerciseAdviceCard.vue'
import AchievementBanner from '@/components/exercise/AchievementBanner.vue'

const store = useExerciseStore()
const { overview, status, records, weekTrend, advice, achievement, loading, error } =
  storeToRefs(store)

onMounted(() => store.load())
</script>

<template>
  <div class="exercise-view">
    <div class="scroll-area">
      <div class="stack">
        <AppHeader title="运动分析" />

        <div v-if="error" class="banner-error">加载失败：{{ error }}</div>

        <ExerciseBanner />

        <div class="grid">
          <div class="col-left">
            <TodayOverviewCard :overview="overview" />
            <TodayRecordsCard :records="records" />
            <WeekTrendChart :trend="weekTrend" :goal="overview?.steps_goal ?? null" />
          </div>
          <div class="col-right">
            <TodayStatusCard :status="status" />
            <ExerciseAdviceCard :advice="advice" />
          </div>
        </div>

        <AchievementBanner :achievement="achievement" />

        <div v-if="loading" class="loading">加载中…</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.exercise-view {
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
.stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 1120px;
}
.grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
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
.banner-error {
  background: #fbe6e6;
  color: #d65a5a;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
}
.loading {
  text-align: center;
  font-size: 13px;
  color: var(--c-text-tertiary);
  padding: 8px;
}
</style>
