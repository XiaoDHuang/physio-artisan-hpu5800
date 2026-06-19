/**
 * 报告图片导出 composable
 *
 * 从 useReportStore 收集当前看板锚点日数据，调用 POST /api/report-image 生成 PNG。
 * 仅当该日已有 AI 报告（hasReport）时允许导出。
 * 切日方案 B：进行中切日 abort；完成时仅看板日 === 锚点日才弹预览。
 */
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useReportStore } from '@/stores/report'
import { exportDateSwitchInfoToast, exportSuccessToast } from '@/copy/reportChat'

const NO_REPORT_MSG = '该日暂无 AI 报告，请先在下方对话中生成后再导出'

export type ExportOutcome =
  | { kind: 'preview'; url: string; anchorDate: string }
  | { kind: 'dismissed'; anchorDate: string }
  | { kind: 'cancelled' }
  | { kind: 'failed' }

export function useReportExport() {
  const isLoading = ref(false)
  const errorMsg = ref<string | null>(null)

  let activeController: AbortController | null = null
  let exportGeneration = 0
  let abortSilently = false

  function buildReportData() {
    const store = useReportStore()
    const body = store.body || {}
    const sleep = store.sleep || {}
    const nutrition = store.nutrition || {}
    const exercise = store.exerciseToday || {}
    const advice = store.healthAdvice

    if (!store.canExportReport || !advice) {
      return null
    }

    return {
      date: store.date,
      kpi: {
        health_score: store.kpi?.health_score ?? null,
        score_delta_vs_last_week: store.kpi?.score_delta_vs_last_week ?? null,
        status: store.kpi?.status ?? '',
        exercise_rate: store.kpi?.exercise_rate ?? null,
        exercise_rate_delta: store.kpi?.exercise_rate_delta ?? null,
        risk: store.kpi?.risk ?? '',
      },
      body: {
        heart_rate: (body as Record<string, unknown>).heart_rate ?? null,
        weight_kg: (body as Record<string, unknown>).weight_kg ?? null,
        bmi: (body as Record<string, unknown>).bmi ?? null,
        bmr: (body as Record<string, unknown>).bmr ?? null,
        body_fat_pct: (body as Record<string, unknown>).body_fat_pct ?? null,
        muscle_mass_kg: (body as Record<string, unknown>).muscle_mass_kg ?? null,
        update_date: (body as Record<string, unknown>).update_date ?? '',
      },
      sleep: {
        score: (sleep as Record<string, unknown>).score ?? null,
        total_hours: (sleep as Record<string, unknown>).total_hours ?? null,
        deep_sleep_percent: (sleep as Record<string, unknown>).deep_sleep_percent ?? null,
      },
      nutrition: {
        total_calories: (nutrition as Record<string, unknown>).total_calories ?? null,
        balance_score: (nutrition as Record<string, unknown>).balance_score ?? null,
      },
      exercise: {
        steps: (exercise as Record<string, unknown>).steps ?? null,
        steps_goal: (exercise as Record<string, unknown>).steps_goal ?? 8000,
        duration_minutes: (exercise as Record<string, unknown>).duration_minutes ?? null,
        calories_burned: (exercise as Record<string, unknown>).calories_burned ?? null,
        intensity: (exercise as Record<string, unknown>).intensity ?? '',
      },
      healthAdvice: {
        exercise: advice.exercise,
        sleep: advice.sleep,
        nutrition: advice.nutrition,
      },
    }
  }

  /** 切日等场景：静默中止进行中的导出 */
  function cancelExportOnDateSwitch() {
    if (!isLoading.value) return
    abortSilently = true
    exportGeneration += 1
    activeController?.abort()
    activeController = null
  }

  async function exportReportImage(): Promise<ExportOutcome | null> {
    const store = useReportStore()
    if (!store.canExportReport) {
      message.info(NO_REPORT_MSG)
      return null
    }

    const data = buildReportData()
    if (!data) {
      message.info(NO_REPORT_MSG)
      return null
    }

    const anchorDate = data.date
    const gen = ++exportGeneration
    abortSilently = false
    isLoading.value = true
    errorMsg.value = null

    activeController?.abort()
    const controller = new AbortController()
    activeController = controller
    const timeout = setTimeout(() => controller.abort(), 120000)

    try {
      const resp = await fetch('/api/report-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        signal: controller.signal,
      })
      clearTimeout(timeout)

      if (gen !== exportGeneration) {
        return { kind: 'cancelled' }
      }

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: `服务返回 ${resp.status}` }))
        throw new Error(err.error || `服务返回 ${resp.status}`)
      }

      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)

      if (gen !== exportGeneration) {
        URL.revokeObjectURL(url)
        return { kind: 'cancelled' }
      }

      const viewingDate = useReportStore().date
      if (viewingDate === anchorDate) {
        message.success(exportSuccessToast(anchorDate))
        return { kind: 'preview', url, anchorDate }
      }

      URL.revokeObjectURL(url)
      message.info(exportDateSwitchInfoToast(anchorDate))
      return { kind: 'dismissed', anchorDate }
    } catch (e: unknown) {
      clearTimeout(timeout)
      if (gen !== exportGeneration || abortSilently) {
        abortSilently = false
        return { kind: 'cancelled' }
      }
      if (e instanceof Error && e.name === 'AbortError') {
        errorMsg.value = '生成超时，请稍后重试'
      } else {
        errorMsg.value = e instanceof Error ? e.message : '报告图片生成失败，请稍后重试'
      }
      return { kind: 'failed' }
    } finally {
      if (gen === exportGeneration) {
        isLoading.value = false
        activeController = null
      }
    }
  }

  function downloadImage(url: string, filename: string) {
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  function filenameForDate(dateStr: string): string {
    return `健康报告-${dateStr}.png`
  }

  return {
    isLoading,
    errorMsg,
    buildReportData,
    exportReportImage,
    cancelExportOnDateSwitch,
    downloadImage,
    filenameForDate,
    noReportMessage: NO_REPORT_MSG,
  }
}
