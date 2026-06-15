<script setup lang="ts">
// 今日运动记录：多条（类型 / 时间段 / 距离或时长 / 消耗）
import type { ExerciseRecord } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import iconRun from '@/assets/page-exercise/户外跑步.png'
import iconStrength from '@/assets/page-exercise/力量训练.png'
import iconYoga from '@/assets/page-exercise/瑜伽.png'

defineProps<{ records: ExerciseRecord[] }>()

function iconFor(type: string) {
  if (type.includes('跑')) return iconRun
  if (type.includes('瑜')) return iconYoga
  return iconStrength
}
function isRun(type: string) {
  return type.includes('跑')
}
</script>

<template>
  <SectionCard title="今日运动记录">
    <div v-if="records.length" class="rows">
      <div v-for="(r, i) in records" :key="i" class="row">
        <img :src="iconFor(r.exercise_type)" class="row-icon" alt="" />
        <div class="row-main">
          <div class="row-name">{{ r.exercise_type }}</div>
          <div class="row-time">{{ r.time_range || '—' }}</div>
        </div>
        <div class="row-metric">
          <template v-if="isRun(r.exercise_type) && r.distance_km != null">
            {{ r.distance_km.toFixed(2) }} <span class="u">公里</span>
          </template>
          <template v-else>
            {{ r.duration_minutes ?? '—' }} <span class="u">分钟</span>
          </template>
        </div>
        <div class="row-cal">消耗 {{ r.calories ?? '—' }} <span class="u">kcal</span></div>
      </div>
    </div>
    <div v-else class="empty">今日暂无运动记录</div>
  </SectionCard>
</template>

<style scoped>
.rows {
  display: flex;
  flex-direction: column;
}
.row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 0;
}
.row + .row {
  border-top: 1px solid var(--c-border);
}
.row-icon {
  width: 40px;
  height: 40px;
  object-fit: contain;
  flex-shrink: 0;
}
.row-main {
  flex: 1;
  min-width: 0;
}
.row-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
}
.row-time {
  font-size: 12px;
  color: var(--c-text-tertiary);
  margin-top: 2px;
}
.row-metric {
  font-size: 16px;
  font-weight: 700;
  color: var(--c-text);
  min-width: 90px;
  text-align: center;
}
.row-cal {
  font-size: 13px;
  color: var(--c-text-secondary);
  min-width: 110px;
  text-align: right;
}
.u {
  font-size: 12px;
  color: var(--c-text-tertiary);
  font-weight: 400;
}
.empty {
  padding: 28px 0;
  text-align: center;
  font-size: 13px;
  color: var(--c-text-tertiary);
}
</style>
