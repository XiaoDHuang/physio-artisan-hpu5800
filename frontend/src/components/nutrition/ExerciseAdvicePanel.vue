<script setup lang="ts">
// 运动建议：类型/时长/消耗目标 + 推荐运动方案（组数×次数 / 时长）
import { computed } from 'vue'
import type { NutritionExerciseAdvice, NutritionExerciseItem } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import icType from '@/assets/page-nutrition/运动类型.png'
import icDuration from '@/assets/page-nutrition/运动时长.png'
import icTarget from '@/assets/page-nutrition/消耗目标.png'
import icSquat from '@/assets/page-nutrition/深蹲.png'
import icPushup from '@/assets/page-nutrition/俯卧撑.png'
import icDeadlift from '@/assets/page-nutrition/硬拉.png'
import icStretch from '@/assets/page-nutrition/拉伸放松.png'

const props = defineProps<{ advice: NutritionExerciseAdvice | null }>()

const dash = (v: number | string | null | undefined) => (v == null || v === '' ? '—' : v)

const infos = computed(() => [
  { key: 't', icon: icType, label: '运动类型', value: dash(props.advice?.training_type) },
  { key: 'd', icon: icDuration, label: '运动时长', value: dash(props.advice?.duration) },
  { key: 'c', icon: icTarget, label: '消耗目标', value: props.advice?.calorie_target != null ? `${props.advice.calorie_target} 千卡` : '—' },
])

const EX_ICONS: Record<string, string> = {
  深蹲: icSquat, 俯卧撑: icPushup, 硬拉: icDeadlift, 拉伸放松: icStretch, 拉伸: icStretch,
}
function exIcon(name: string): string | null {
  if (EX_ICONS[name]) return EX_ICONS[name]
  const k = Object.keys(EX_ICONS).find((key) => name.includes(key) || key.includes(name))
  return k ? EX_ICONS[k] : null
}
function exAmount(it: NutritionExerciseItem): string {
  if (it.sets != null && it.reps != null) return `${it.sets} 组 × ${it.reps} 次`
  if (it.duration) return it.duration
  return '—'
}
</script>

<template>
  <SectionCard title="运动建议">
    <div class="tip">
      今天摄入能量低于目标，建议通过运动消耗来促进能量平衡和体质管理。
    </div>

    <div class="sub-title">今日建议</div>
    <div class="infos">
      <div v-for="i in infos" :key="i.key" class="info">
        <img :src="i.icon" class="info-ic" alt="" />
        <span class="info-label">{{ i.label }}</span>
        <span class="info-value">{{ i.value }}</span>
      </div>
    </div>

    <div class="sub-title">推荐运动方案</div>
    <div class="ex-list">
      <div v-for="(ex, i) in advice?.exercises || []" :key="i" class="ex">
        <div class="ex-ic">
          <img v-if="exIcon(ex.name)" :src="exIcon(ex.name)!" :alt="ex.name" />
          <span v-else class="ph">{{ ex.name.slice(0, 1) }}</span>
        </div>
        <span class="ex-name">{{ ex.name }}</span>
        <span class="ex-amount">{{ exAmount(ex) }}</span>
      </div>
    </div>
  </SectionCard>
</template>

<style scoped>
.tip {
  background: var(--c-primary-soft);
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--c-text-secondary);
  margin-bottom: 16px;
}
.sub-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--c-text);
  margin: 14px 0 10px;
}
.infos {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.info {
  display: flex;
  align-items: center;
  gap: 10px;
}
.info-ic {
  width: 26px;
  height: 26px;
  object-fit: contain;
}
.info-label {
  font-size: 13px;
  color: var(--c-text-secondary);
}
.info-value {
  margin-left: auto;
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
}
.ex-list {
  display: flex;
  flex-direction: column;
}
.ex {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
}
.ex + .ex {
  border-top: 1px solid var(--c-border);
}
.ex-ic {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: #f7faf9;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.ex-ic img {
  width: 26px;
  height: 26px;
  object-fit: contain;
}
.ph {
  font-size: 15px;
  color: var(--c-text-tertiary);
}
.ex-name {
  font-size: 14px;
  color: var(--c-text);
}
.ex-amount {
  margin-left: auto;
  font-size: 13px;
  color: var(--c-text-secondary);
}
</style>
