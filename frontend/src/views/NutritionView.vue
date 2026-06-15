<script setup lang="ts">
// 饮食管理页：AppHeader + 顶部KPI(日期切换) + 能量概览 + 左(饮食记录) 右(运动建议/能康助手)
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useNutritionStore } from '@/stores/nutrition'
import AppHeader from '@/components/common/AppHeader.vue'
import NutritionKpiBar from '@/components/nutrition/NutritionKpiBar.vue'
import EnergyOverviewCard from '@/components/nutrition/EnergyOverviewCard.vue'
import MealRecordsCard from '@/components/nutrition/MealRecordsCard.vue'
import ExerciseAdvicePanel from '@/components/nutrition/ExerciseAdvicePanel.vue'
import NutritionChatDock from '@/components/nutrition/NutritionChatDock.vue'

const store = useNutritionStore()
const { kpi, energy, meals, exerciseAdvice, date, error } = storeToRefs(store)

onMounted(() => store.load())
</script>

<template>
  <div class="nutrition-view">
    <div class="scroll-area">
      <div class="stack">
        <AppHeader title="饮食管理" />

        <div v-if="error" class="banner-error">加载失败：{{ error }}</div>

        <NutritionKpiBar :kpi="kpi" :date="date" @prev="store.prevDay()" @next="store.nextDay()" />

        <EnergyOverviewCard :energy="energy" />

        <div class="grid">
          <div class="col-left">
            <MealRecordsCard :meals="meals" />
          </div>
          <div class="col-right">
            <ExerciseAdvicePanel :advice="exerciseAdvice" />
            <NutritionChatDock />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nutrition-view {
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
.banner-error {
  background: #fbe6e6;
  color: #d65a5a;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
}
</style>
