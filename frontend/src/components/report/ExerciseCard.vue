<script setup lang="ts">
import { computed } from 'vue'
import type { ExerciseTodayPanel, WeekSummary } from '@/api/types'
import SectionCard from './SectionCard.vue'

const props = defineProps<{
  exercise: ExerciseTodayPanel | null
  week: WeekSummary | null
}>()

const steps = computed(() => props.exercise?.steps ?? 0)
const goal = computed(() => props.exercise?.steps_goal ?? 8000)
const pct = computed(() => Math.min(100, goal.value ? (steps.value / goal.value) * 100 : 0))

const dash = (v: number | null | undefined, u = '') =>
  v === null || v === undefined ? '—' : `${v}${u}`

const stats = computed(() => [
  { label: '运动时长', value: dash(props.exercise?.duration_minutes), unit: '分钟' },
  { label: '消耗热量', value: dash(props.exercise?.calories_burned), unit: '千卡' },
  { label: '运动强度', value: props.exercise?.intensity || '—', unit: '' },
])
</script>

<template>
  <SectionCard title="运动监测" more>
    <div class="today">今日步数</div>
    <div class="steps">
      {{ dash(exercise?.steps) }}<span class="goal">/{{ goal }} 步</span>
    </div>
    <div class="track"><div class="fill" :style="{ width: pct + '%' }" /></div>

    <div class="stats">
      <div v-for="s in stats" :key="s.label" class="stat">
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-value">{{ s.value }}<span class="stat-unit">{{ s.unit }}</span></div>
      </div>
    </div>

    <div class="footer">
      <span>本周运动 <b>{{ dash(week?.workout_days) }}/{{ week?.days_goal ?? 7 }}</b> 天</span>
      <span>累计消耗 <b>{{ dash(week?.total_calories_burned) }}</b> 千卡</span>
    </div>
  </SectionCard>
</template>

<style scoped>
.today {
  font-size: 13px;
  color: var(--c-text-secondary);
}
.steps {
  font-size: 30px;
  font-weight: 800;
  color: var(--c-primary-hover);
  line-height: 1.2;
  margin-top: 2px;
}
.goal {
  font-size: 14px;
  font-weight: 500;
  color: var(--c-text-tertiary);
  margin-left: 4px;
}
.track {
  height: 8px;
  background: #eef3f1;
  border-radius: 4px;
  overflow: hidden;
  margin: 12px 0 16px;
}
.fill {
  height: 100%;
  background: linear-gradient(90deg, #7cd9b3, var(--c-primary));
  border-radius: 4px;
}
.stats {
  display: flex;
  justify-content: space-between;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--c-border);
}
.stat-label {
  font-size: 12px;
  color: var(--c-text-tertiary);
}
.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--c-text);
  margin-top: 2px;
}
.stat-unit {
  font-size: 11px;
  font-weight: 500;
  color: var(--c-text-tertiary);
  margin-left: 2px;
}
.footer {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  font-size: 13px;
  color: var(--c-text-secondary);
}
.footer b {
  color: var(--c-text);
}
</style>
