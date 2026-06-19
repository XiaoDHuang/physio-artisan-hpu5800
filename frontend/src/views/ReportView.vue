<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useReportStore } from '@/stores/report'
import { useUserStore } from '@/stores/user'
import { useChatStore } from '@/stores/chat'
import { useReportExport } from '@/composables/useReportExport'
import AppHeader from '@/components/common/AppHeader.vue'
import KpiCards from '@/components/report/KpiCards.vue'
import BodyOverview from '@/components/report/BodyOverview.vue'
import SectionCard from '@/components/report/SectionCard.vue'
import HealthAdviceCard from '@/components/report/HealthAdviceCard.vue'
import SleepCard from '@/components/report/SleepCard.vue'
import NutritionCard from '@/components/report/NutritionCard.vue'
import ExerciseCard from '@/components/report/ExerciseCard.vue'
import ChatDock from '@/components/report/ChatDock.vue'

const store = useReportStore()
const userStore = useUserStore()
const chat = useChatStore()
const { kpi, body, sleep, nutrition, exerciseToday, weekSummary, healthAdvice, date, loading, isToday, hasReport } =
  storeToRefs(store)

const reportDatePill = computed(() => (date.value ? `${date.value}健康数据` : '健康数据'))
const reportDateDisplay = computed(() => {
  const d = date.value
  if (!d) return '—'
  const [y, m, day] = d.split('-')
  return `${y} - ${m} - ${day}`
})

const { isLoading, errorMsg, exportReportImage, downloadImage } = useReportExport()
const previewUrl = ref<string | null>(null)

onMounted(() => {
  store.load()
})

watch(
  () => userStore.reloadVersion,
  () => {
    previewUrl.value = null
  },
)

// 场景 1：报告生成中切换日期 — 清 Chat 展示态，任务继续
watch(
  () => date.value,
  (next, prev) => {
    if (prev && next !== prev && chat.isReportRunning) {
      chat.clearConversationUi()
    }
  },
)

async function onExport() {
  const url = await exportReportImage()
  if (url) {
    previewUrl.value = url
  }
}

function closePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
}

async function onReportComplete() {
  // 看板刷新与 toast 由 chat store.onReportTaskSettled 处理
}
</script>

<template>
  <div class="report-view">
    <div class="scroll-area">
      <div class="report-content">
      <AppHeader title="健康报告" subtitle="基于您的运动、睡眠、饮食等数据综合分析">
        <span class="hdr-pill">{{ reportDatePill }}</span>
        <span class="hdr-pill hdr-date-nav">
          <button type="button" class="hdr-nav" :disabled="loading" title="前一天" @click="store.prevDay()">‹</button>
          <span class="hdr-date-inner">
            <svg class="hdr-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            {{ reportDateDisplay }}
          </span>
          <button type="button" class="hdr-nav" :disabled="loading || isToday" title="后一天" @click="store.nextDay()">›</button>
        </span>
        <button class="hdr-export" :disabled="isLoading" @click="onExport">
          <svg class="hdr-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          {{ isLoading ? '正在生成报告图片...' : '导出报告' }}
        </button>
      </AppHeader>

      <!-- 顶部 4 KPI -->
      <KpiCards :kpi="kpi" />

      <!-- 主体两栏：左宽(身体概览+健康建议) / 右窄(睡眠/饮食/运动) -->
      <div class="grid">
        <div class="col-left">
          <SectionCard title="身体指标概览">
            <BodyOverview :body="body" />
          </SectionCard>
          <HealthAdviceCard
            :advice="healthAdvice"
            :empty-hint="hasReport ? undefined : '该日暂无 AI 报告，可在下方对话中生成'"
          />
        </div>

        <div class="col-right">
          <SleepCard :sleep="sleep" />
          <NutritionCard :nutrition="nutrition" />
          <ExerciseCard :exercise="exerciseToday" :week="weekSummary" />
        </div>
      </div>

      <!-- 底部聊天卡片（整宽）-->
      <ChatDock
        :user-id="userStore.userId"
        :user-name="userStore.userName"
        :report-date="date"
        :on-report-complete="onReportComplete"
      />
      </div>
    </div>

    <!-- 报告图片预览弹窗 -->
    <Transition name="modal">
      <div v-if="previewUrl" class="preview-overlay" @click.self="closePreview">
        <div class="preview-box">
          <img :src="previewUrl" class="preview-img" alt="报告图片" />
          <div class="preview-actions">
            <button class="preview-btn" @click="downloadImage(previewUrl!, '健康报告-' + new Date().toISOString().slice(0,10) + '.png')">下载</button>
            <button class="preview-btn secondary" @click="closePreview">关闭</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 错误提示 -->
    <Transition name="toast">
      <div v-if="errorMsg" class="export-error-toast">{{ errorMsg }}</div>
    </Transition>
  </div>
</template>

<style scoped>
.report-view {
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
.report-content {
  min-width: 1120px;
}
.grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
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

/* Header 中间槽：健康数据标签 / 日期 / 导出报告 */
.hdr-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 14px;
  background: #f3f5f7;
  border-radius: 8px;
  font-size: 13px;
  color: #5f6b66;
  white-space: nowrap;
}
.hdr-date {
  color: #3d3d3d;
}
.hdr-date-nav {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 6px;
  color: #3d3d3d;
}
.hdr-date-inner {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 6px;
  min-width: 130px;
  justify-content: center;
}
.hdr-nav {
  width: 26px;
  height: 26px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 18px;
  line-height: 1;
  color: var(--c-text-secondary);
  cursor: pointer;
}
.hdr-nav:hover:not(:disabled) {
  background: #e8ecea;
  color: var(--c-primary-hover);
}
.hdr-nav:disabled {
  opacity: 0.35;
  cursor: default;
}
.hdr-export {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 16px;
  border: none;
  border-radius: 8px;
  background: var(--c-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.hdr-export:hover:not(:disabled) {
  background: var(--c-primary-hover);
}
.hdr-export:disabled {
  opacity: 0.7;
  cursor: wait;
}
.hdr-ico {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

/* 报告图片预览弹窗 */
.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-box {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 90vw;
  max-height: 90vh;
}
.preview-img {
  max-width: 100%;
  max-height: calc(90vh - 100px);
  object-fit: contain;
  border-radius: 8px;
}
.preview-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}
.preview-btn {
  padding: 10px 28px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: var(--c-primary);
  color: #fff;
}
.preview-btn.secondary {
  background: var(--c-primary-soft);
  color: var(--c-primary-hover);
}
.preview-btn:hover {
  opacity: 0.85;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

/* 错误提示 */
.export-error-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(239, 68, 68, 0.92);
  color: #fff;
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  z-index: 9999;
  white-space: nowrap;
}
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}
</style>
