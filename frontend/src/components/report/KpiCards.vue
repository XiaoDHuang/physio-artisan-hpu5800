<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardKpi } from '@/api/types'
import iconScore from '@/assets/top-4-kpi-icon/综合健康评分.png'
import iconStatus from '@/assets/top-4-kpi-icon/身体状态.png'
import iconStatusRB from '@/assets/top-4-kpi-icon/身体状态-righ-bottom.png'
import iconRate from '@/assets/top-4-kpi-icon/运动达标率.png'
import iconRisk from '@/assets/top-4-kpi-icon/健康风险.png'
import iconRiskRB from '@/assets/top-4-kpi-icon/健康风险-right-bottom.png'

const props = defineProps<{ kpi: DashboardKpi | null }>()

const dash = (v: number | null | undefined) => (v === null || v === undefined ? '—' : v)

function deltaText(v: number | null | undefined): string {
  if (v === null || v === undefined || v === 0) return '较上周持平'
  return v > 0 ? `较上周 ↑ ${v}` : `较上周 ↓ ${Math.abs(v)}`
}

const cards = computed(() => {
  const k = props.kpi
  return [
    {
      key: 'score',
      label: '综合健康评分',
      icon: iconScore,
      rb: '',
      value: dash(k?.health_score),
      unit: '/100',
      sub: deltaText(k?.score_delta_vs_last_week),
    },
    {
      key: 'status',
      label: '身体状态',
      icon: iconStatus,
      rb: iconStatusRB,
      value: k?.status || '—',
      unit: '',
      sub: '活力充沛',
    },
    {
      key: 'rate',
      label: '运动达标率',
      icon: iconRate,
      rb: '',
      value: k?.exercise_rate === null || k?.exercise_rate === undefined ? '—' : k.exercise_rate + '%',
      unit: '',
      sub: deltaText(k?.exercise_rate_delta) + (k?.exercise_rate_delta ? '%' : ''),
    },
    {
      key: 'risk',
      label: '健康风险',
      icon: iconRisk,
      rb: iconRiskRB,
      value: k?.risk || '—',
      unit: '',
      sub: '一切指标正常',
    },
  ]
})
</script>

<template>
  <div class="kpi-row">
    <div v-for="c in cards" :key="c.key" class="kpi-card">
      <img :src="c.icon" class="kpi-icon" alt="" />
      <div class="kpi-content">
        <div class="kpi-label">{{ c.label }}</div>
        <div class="kpi-value">
          {{ c.value }}<span v-if="c.unit" class="kpi-unit">{{ c.unit }}</span>
        </div>
        <div class="kpi-sub">{{ c.sub }}</div>
      </div>
      <img v-if="c.rb" :src="c.rb" class="kpi-rb" alt="" />
    </div>
  </div>
</template>

<style scoped>
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 18px;
}
.kpi-card {
  position: relative;
  background: var(--c-card-bg);
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(31, 45, 40, 0.06);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  overflow: hidden;
  min-height: 96px;
}
.kpi-icon {
  width: 46px;
  height: 46px;
  object-fit: contain;
  flex-shrink: 0;
}
.kpi-content {
  min-width: 0;
}
.kpi-label {
  font-size: 13px;
  color: var(--c-text-secondary);
}
.kpi-value {
  font-size: 26px;
  font-weight: 800;
  color: var(--c-text);
  line-height: 1.2;
  margin-top: 2px;
}
.kpi-unit {
  font-size: 14px;
  font-weight: 500;
  color: var(--c-text-tertiary);
  margin-left: 2px;
}
.kpi-sub {
  font-size: 12px;
  color: var(--c-primary-hover);
  margin-top: 2px;
}
.kpi-rb {
  position: absolute;
  right: 10px;
  bottom: 8px;
  width: 40px;
  height: 40px;
  object-fit: contain;
  opacity: 0.9;
}
</style>
