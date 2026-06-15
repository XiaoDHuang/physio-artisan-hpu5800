<script setup lang="ts">
// 睡眠监测页：AppHeader + 今日概况 + 左(时间/小憩/趋势/建议) 右(睡眠情况/录入)
import { onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useSleepStore } from '@/stores/sleep'
import type { SleepRangeOpt } from '@/api/sleep'
import AppHeader from '@/components/common/AppHeader.vue'
import SleepScoreCard from '@/components/sleep/SleepScoreCard.vue'
import RangeBarCard from '@/components/sleep/RangeBarCard.vue'
import SleepDetailCard from '@/components/sleep/SleepDetailCard.vue'
import SleepTrendChart from '@/components/sleep/SleepTrendChart.vue'
import SleepAdviceTabs from '@/components/sleep/SleepAdviceTabs.vue'
import SleepEntryForm from '@/components/sleep/SleepEntryForm.vue'

const store = useSleepStore()
const { today, duration, nap, trend, advice, foods, range, error } = storeToRefs(store)

onMounted(() => store.load())

function fmtDuration(h: number | null | undefined): string {
  if (h == null) return '—'
  const hh = Math.floor(h)
  const mm = Math.round((h - hh) * 60)
  const tail = mm ? ` <span class="num">${mm}</span><span class="u">分钟</span>` : ''
  return `<span class="num">${hh}</span><span class="u">小时</span>${tail}`
}

// 今日睡眠时间卡
const durationProps = computed(() => ({
  title: '今日睡眠时间',
  status: duration.value?.status || '—',
  mainText: fmtDuration(today.value?.total_hours),
  recommendLabel: `推荐时长 ${duration.value?.recommend_min ?? 7}-${duration.value?.recommend_max ?? 9} 小时`,
  value: today.value?.total_hours ?? null,
  recommendMin: duration.value?.recommend_min ?? 7,
  recommendMax: duration.value?.recommend_max ?? 9,
  scaleMax: 12,
  ticks: [
    { label: '0', value: 0 },
    { label: `${duration.value?.recommend_min ?? 7}h`, value: duration.value?.recommend_min ?? 7 },
    { label: `${duration.value?.recommend_max ?? 9}h`, value: duration.value?.recommend_max ?? 9 },
    { label: '12h', value: 12 },
  ],
  fillColor: '#5fb98f',
}))

// 今日小憩时间卡
const napProps = computed(() => ({
  title: '今日小憩时间',
  status: nap.value?.status || '—',
  mainText: `<span class="num">${today.value?.nap_minutes ?? '—'}</span><span class="u">分钟</span>`,
  recommendLabel: `推荐时长 ${nap.value?.recommend_min ?? 20}-${nap.value?.recommend_max ?? 30} 分钟`,
  value: today.value?.nap_minutes ?? null,
  recommendMin: nap.value?.recommend_min ?? 20,
  recommendMax: nap.value?.recommend_max ?? 30,
  scaleMax: 60,
  ticks: [
    { label: '0', value: 0 },
    { label: `${nap.value?.recommend_min ?? 20}m`, value: nap.value?.recommend_min ?? 20 },
    { label: `${nap.value?.recommend_max ?? 30}m`, value: nap.value?.recommend_max ?? 30 },
    { label: '60m', value: 60 },
  ],
  fillColor: '#9b8cf5',
}))

function onChangeRange(v: SleepRangeOpt) {
  store.load(v)
}
</script>

<template>
  <div class="sleep-view">
    <div class="scroll-area">
      <div class="stack">
        <AppHeader title="睡眠监测" />

        <div v-if="error" class="banner-error">加载失败：{{ error }}</div>

        <SleepScoreCard :today="today" />

        <div class="grid">
          <div class="col-left">
            <div class="duo">
              <RangeBarCard v-bind="durationProps" />
              <RangeBarCard v-bind="napProps" />
            </div>
            <SleepTrendChart :trend="trend" :range="range" @change-range="onChangeRange" />
            <SleepAdviceTabs :advice="advice" :foods="foods" />
          </div>
          <div class="col-right">
            <SleepDetailCard :today="today" />
            <SleepEntryForm />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sleep-view {
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
.duo {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.duo > * {
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
