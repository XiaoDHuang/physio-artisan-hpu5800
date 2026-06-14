<script setup lang="ts">
// 今日睡眠情况：入睡 / 起床 / 睡眠时长 / 深度睡眠
import { computed } from 'vue'
import type { SleepToday } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import iconBed from '@/assets/page-sleep/入睡时间.png'
import iconWake from '@/assets/page-sleep/起床时间.png'
import iconDuration from '@/assets/page-sleep/睡眠时长.png'
import iconDeep from '@/assets/page-sleep/深度睡眠.png'

const props = defineProps<{ today: SleepToday | null }>()

function fmtHours(h: number | null | undefined): string {
  if (h == null) return '—'
  const hh = Math.floor(h)
  const mm = Math.round((h - hh) * 60)
  return mm ? `${hh} 小时 ${mm} 分钟` : `${hh} 小时`
}

const rows = computed(() => {
  const t = props.today
  return [
    { key: 'bed', icon: iconBed, label: '入睡时间', value: t?.bedtime || '—' },
    { key: 'wake', icon: iconWake, label: '起床时间', value: t?.wake_time || '—' },
    { key: 'dur', icon: iconDuration, label: '睡眠时长', value: fmtHours(t?.total_hours) },
    { key: 'deep', icon: iconDeep, label: '深度睡眠', value: fmtHours(t?.deep_sleep_hours) },
  ]
})
</script>

<template>
  <SectionCard title="今日睡眠情况">
    <div class="rows">
      <div v-for="r in rows" :key="r.key" class="row">
        <img :src="r.icon" class="row-icon" alt="" />
        <span class="row-label">{{ r.label }}</span>
        <span class="row-value">{{ r.value }}</span>
      </div>
    </div>
    <div class="more">查看详情 ›</div>
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
  gap: 12px;
  padding: 13px 0;
}
.row + .row {
  border-top: 1px solid var(--c-border);
}
.row-icon {
  width: 34px;
  height: 34px;
  object-fit: contain;
  flex-shrink: 0;
}
.row-label {
  flex: 1;
  font-size: 14px;
  color: var(--c-text-secondary);
}
.row-value {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-text);
}
.more {
  text-align: center;
  margin-top: 12px;
  font-size: 13px;
  color: var(--c-primary-hover);
  cursor: pointer;
}
</style>
