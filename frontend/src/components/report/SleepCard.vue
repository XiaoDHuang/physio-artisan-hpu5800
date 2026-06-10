<script setup lang="ts">
import { computed } from 'vue'
import type { SleepPanel } from '@/api/types'
import SectionCard from './SectionCard.vue'

const props = defineProps<{ sleep: SleepPanel | null }>()

const score = computed(() => props.sleep?.score ?? 0)
const scoreLabel = computed(() => {
  const s = score.value
  return s >= 80 ? '良好' : s >= 60 ? '一般' : '欠佳'
})
const ringStyle = computed(() => ({
  background: `conic-gradient(var(--c-primary) ${score.value * 3.6}deg, #eef3f1 0)`,
}))

// 柱状：每小时 浅睡(light)/深睡(deep) 堆叠，高度按分钟归一
const bars = computed(() => {
  const tl = props.sleep?.stages_timeline ?? []
  const max = Math.max(60, ...tl.map((s) => (s.deep || 0) + (s.light || 0)))
  return tl.map((s, i) => ({
    hour: i,
    deepH: ((s.deep || 0) / max) * 100,
    lightH: ((s.light || 0) / max) * 100,
  }))
})
</script>

<template>
  <SectionCard title="睡眠监测" more>
    <div class="sleep-body">
      <div class="ring-wrap">
        <div class="ring" :style="ringStyle">
          <div class="ring-inner">
            <div class="ring-label">睡眠评分</div>
            <div class="ring-score">{{ score || '—' }}</div>
            <div class="ring-state">{{ scoreLabel }}</div>
          </div>
        </div>
      </div>

      <div class="legend">
        <span class="dot light" /> 浅睡
        <span class="dot deep" /> 深睡
      </div>

      <div class="bars">
        <div v-for="b in bars" :key="b.hour" class="bar-col">
          <div class="bar light" :style="{ height: b.lightH + '%' }" />
          <div class="bar deep" :style="{ height: b.deepH + '%' }" />
        </div>
        <div v-if="!bars.length" class="bars-empty">暂无睡眠分时数据</div>
      </div>
      <div class="x-axis">
        <span v-for="b in bars" :key="b.hour">{{ b.hour }}</span>
      </div>
    </div>
  </SectionCard>
</template>

<style scoped>
.sleep-body {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.ring {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ring-inner {
  width: 92px;
  height: 92px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.ring-label {
  font-size: 11px;
  color: var(--c-text-tertiary);
}
.ring-score {
  font-size: 30px;
  font-weight: 800;
  color: var(--c-text);
  line-height: 1.1;
}
.ring-state {
  font-size: 11px;
  color: var(--c-primary-hover);
}
.legend {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--c-text-secondary);
  margin: 16px 0 10px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  display: inline-block;
}
.dot.light {
  background: #b9c6f7;
}
.dot.deep {
  background: #6a73d8;
}
.dot + .dot {
  margin-left: 10px;
}
.bars {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 90px;
  width: 100%;
  padding: 0 4px;
}
.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column-reverse;
  height: 100%;
}
.bar {
  width: 100%;
  border-radius: 3px;
}
.bar.deep {
  background: #6a73d8;
}
.bar.light {
  background: #b9c6f7;
}
.bars-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--c-text-tertiary);
}
.x-axis {
  display: flex;
  justify-content: space-between;
  width: 100%;
  padding: 4px 4px 0;
  font-size: 10px;
  color: var(--c-text-tertiary);
}
</style>
