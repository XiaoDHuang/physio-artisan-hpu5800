<script setup lang="ts">
// 睡眠时间录入：入睡/起床（日期+时间）→ POST /sleep/entry → 成功后回刷
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useSleepStore } from '@/stores/sleep'
import SectionCard from '@/components/report/SectionCard.vue'
import icHeader from '@/assets/page-sleep/睡眠时间录入.svg'
import icBed from '@/assets/page-sleep/睡眠时间录入-入睡时间.svg'
import icWake from '@/assets/page-sleep/睡眠时间录入-起床时间.svg'

const store = useSleepStore()

// antd DatePicker / TimePicker 返回 dayjs 实例
const bedDate = ref<any>(null)
const bedTime = ref<any>(null)
const wakeDate = ref<any>(null)
const wakeTime = ref<any>(null)

async function onSave() {
  if (!bedDate.value || !bedTime.value || !wakeDate.value || !wakeTime.value) {
    message.warning('请填写完整的入睡与起床时间')
    return
  }
  const bedtime = `${bedDate.value.format('YYYY-MM-DD')}T${bedTime.value.format('HH:mm')}`
  const wake_time = `${wakeDate.value.format('YYYY-MM-DD')}T${wakeTime.value.format('HH:mm')}`
  const ok = await store.saveEntry({
    bedtime,
    wake_time,
    on_date: bedDate.value.format('YYYY-MM-DD'),
  })
  if (ok) message.success('已保存睡眠记录')
  else message.error(store.error || '保存失败')
}
</script>

<template>
  <SectionCard>
    <div class="head">
      <img :src="icHeader" class="head-ic" alt="" />
      <div>
        <div class="title">睡眠时间录入</div>
        <div class="sub">记录睡眠时间，更准确分析睡眠质量！</div>
      </div>
    </div>

    <div class="field">
      <div class="field-label"><img :src="icBed" class="f-ic" alt="" />入睡时间</div>
      <div class="field-inputs">
        <a-date-picker v-model:value="bedDate" placeholder="日期" style="width: 100%" />
        <a-time-picker v-model:value="bedTime" format="HH:mm" placeholder="时间" style="width: 100%" />
      </div>
    </div>

    <div class="field">
      <div class="field-label"><img :src="icWake" class="f-ic" alt="" />起床时间</div>
      <div class="field-inputs">
        <a-date-picker v-model:value="wakeDate" placeholder="日期" style="width: 100%" />
        <a-time-picker v-model:value="wakeTime" format="HH:mm" placeholder="时间" style="width: 100%" />
      </div>
    </div>

    <button class="save-btn" :disabled="store.saving" @click="onSave">
      {{ store.saving ? '保存中…' : '保存记录' }}
    </button>
  </SectionCard>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}
.head-ic {
  width: 34px;
  height: 34px;
  object-fit: contain;
}
.title {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-text);
}
.sub {
  font-size: 12px;
  color: var(--c-text-tertiary);
  margin-top: 2px;
}
.field {
  background: #f7faf9;
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
}
.field-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-secondary);
  margin-bottom: 10px;
}
.f-ic {
  width: 18px;
  height: 18px;
  object-fit: contain;
}
.field-inputs {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.save-btn {
  width: 100%;
  margin-top: 6px;
  border: none;
  background: var(--c-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  padding: 11px 0;
  border-radius: 24px;
  cursor: pointer;
}
.save-btn:hover:not(:disabled) {
  background: var(--c-primary-hover);
}
.save-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
