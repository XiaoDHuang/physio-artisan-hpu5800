<script setup lang="ts">
// 通用「达标进度」卡：大数值 + 达标徽标 + 推荐区间带 + 进度条 + 刻度
import { computed } from 'vue'
import SectionCard from '@/components/report/SectionCard.vue'

const props = defineProps<{
  title: string
  status: string
  mainText: string
  recommendLabel: string
  value: number | null
  recommendMin: number | null
  recommendMax: number | null
  scaleMax: number
  ticks: { label: string; value: number }[]
  fillColor: string
}>()

const tone = computed<'good' | 'warn'>(() =>
  ['达标', '适中'].includes(props.status) ? 'good' : 'warn',
)
const pct = (v: number | null | undefined) =>
  v == null ? 0 : Math.max(0, Math.min(100, (v / props.scaleMax) * 100))
const fillPct = computed(() => pct(props.value))
const bandLeft = computed(() => pct(props.recommendMin))
const bandWidth = computed(() => Math.max(0, pct(props.recommendMax) - pct(props.recommendMin)))
</script>

<template>
  <SectionCard>
    <div class="head">
      <span class="title">{{ title }}</span>
      <span class="badge" :class="tone">{{ status }}</span>
    </div>
    <div class="main" v-html="mainText" />
    <div class="recommend">{{ recommendLabel }}</div>
    <div class="bar">
      <div class="band" :style="{ left: bandLeft + '%', width: bandWidth + '%' }" />
      <div class="fill" :style="{ width: fillPct + '%', background: fillColor }" />
    </div>
    <div class="ticks">
      <span v-for="(t, i) in ticks" :key="i" class="tick" :style="{ left: pct(t.value) + '%' }">
        {{ t.label }}
      </span>
    </div>
  </SectionCard>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-text);
}
.badge {
  font-size: 12px;
  padding: 1px 10px;
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
.main {
  margin: 14px 0 4px;
  color: var(--c-text);
}
.main :deep(.num) {
  font-size: 30px;
  font-weight: 800;
}
.main :deep(.u) {
  font-size: 14px;
  color: var(--c-text-tertiary);
  margin: 0 2px 0 3px;
}
.recommend {
  font-size: 12px;
  color: var(--c-text-tertiary);
  margin-bottom: 14px;
}
.bar {
  position: relative;
  height: 8px;
  border-radius: 4px;
  background: #eef3f1;
  overflow: hidden;
}
.band {
  position: absolute;
  top: 0;
  height: 100%;
  background: rgba(63, 191, 143, 0.18);
}
.fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.ticks {
  position: relative;
  height: 16px;
  margin-top: 6px;
}
.tick {
  position: absolute;
  transform: translateX(-50%);
  font-size: 11px;
  color: var(--c-text-tertiary);
  white-space: nowrap;
}
</style>
