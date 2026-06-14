<script setup lang="ts">
// 今日状态：饮食情况 / 睡眠情况 / 身体疲劳度 三行
import { computed } from 'vue'
import type { ExerciseTodayStatus } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import iconDiet from '@/assets/page-exercise/饮食情况.png'
import iconSleep from '@/assets/page-exercise/睡眠情况.png'
import iconFatigue from '@/assets/page-exercise/身体疲劳度.png'

const props = defineProps<{ status: ExerciseTodayStatus | null }>()

const FATIGUE_LABEL: Record<string, string> = { low: '低', medium: '中等', high: '高' }

// 状态等级 → 徽标色（good 绿 / warn 橙 / bad 红）
function tone(level: string): 'good' | 'warn' | 'bad' {
  if (['良好', '低'].includes(level)) return 'good'
  if (['偏低', '一般', '中等'].includes(level)) return 'warn'
  if (['较差', '高'].includes(level)) return 'bad'
  return 'good'
}

function fmtHours(h: number | null | undefined): string {
  if (h === null || h === undefined) return '—'
  const hh = Math.floor(h)
  const mm = Math.round((h - hh) * 60)
  return mm ? `${hh} 小时 ${mm} 分钟` : `${hh} 小时`
}

const rows = computed(() => {
  const s = props.status
  const fatigueLevel = FATIGUE_LABEL[s?.fatigue.level || ''] || '—'
  return [
    {
      key: 'diet', icon: iconDiet, label: '饮食情况',
      badge: s?.diet.status || '—', tone: tone(s?.diet.status || ''),
      sub: s ? `已摄入 ${s.diet.intake ?? '—'}/${s.diet.goal ?? '—'} kcal` : '—',
    },
    {
      key: 'sleep', icon: iconSleep, label: '睡眠情况',
      badge: s?.sleep.status || '—', tone: tone(s?.sleep.status || ''),
      sub: s ? `睡眠 ${fmtHours(s.sleep.hours)}` : '—',
    },
    {
      key: 'fatigue', icon: iconFatigue, label: '身体疲劳度',
      badge: fatigueLevel, tone: tone(fatigueLevel),
      sub: s?.fatigue.advice || '—',
    },
  ]
})
</script>

<template>
  <SectionCard title="今日状态">
    <div class="rows">
      <div v-for="r in rows" :key="r.key" class="row">
        <img :src="r.icon" class="row-icon" alt="" />
        <div class="row-main">
          <div class="row-top">
            <span class="row-label">{{ r.label }}</span>
            <span class="badge" :class="r.tone">{{ r.badge }}</span>
          </div>
          <div class="row-sub">{{ r.sub }}</div>
        </div>
        <span class="chevron">›</span>
      </div>
    </div>
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
  padding: 12px 0;
}
.row + .row {
  border-top: 1px solid var(--c-border);
}
.row-icon {
  width: 38px;
  height: 38px;
  object-fit: contain;
  flex-shrink: 0;
}
.row-main {
  flex: 1;
  min-width: 0;
}
.row-top {
  display: flex;
  align-items: center;
  gap: 10px;
}
.row-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
}
.badge {
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 8px;
}
.badge.good {
  color: var(--c-primary-hover);
  background: var(--c-primary-soft);
}
.badge.warn {
  color: #d98a1a;
  background: #fdf1de;
}
.badge.bad {
  color: #d65a5a;
  background: #fbe6e6;
}
.row-sub {
  font-size: 12px;
  color: var(--c-text-tertiary);
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chevron {
  color: var(--c-text-tertiary);
  font-size: 18px;
  flex-shrink: 0;
}
</style>
