/**
 * 报告图片导出 composable
 *
 * 从 useReportStore 收集报告数据，调用 POST /api/report-image 后端大模型图片生成，
 * 返回 ObjectURL 供前端展示和下载。
 */
import { ref } from 'vue'
import { useReportStore } from '@/stores/report'

export function useReportExport() {
  const isLoading = ref(false)
  const errorMsg = ref<string | null>(null)

  function buildReportData() {
    const store = useReportStore()
    const body = store.body || {}
    const sleep = store.sleep || {}
    const nutrition = store.nutrition || {}
    const exercise = store.exerciseToday || {}
    const week = store.weekSummary || {}

    return {
      kpi: {
        health_score: store.kpi?.health_score ?? null,
        score_delta_vs_last_week: store.kpi?.score_delta_vs_last_week ?? null,
        status: store.kpi?.status ?? '',
        exercise_rate: store.kpi?.exercise_rate ?? null,
        exercise_rate_delta: store.kpi?.exercise_rate_delta ?? null,
        risk: store.kpi?.risk ?? '',
      },
      body: {
        heart_rate: (body as any).heart_rate ?? null,
        weight_kg: (body as any).weight_kg ?? null,
        bmi: (body as any).bmi ?? null,
        bmr: (body as any).bmr ?? null,
        body_fat_pct: (body as any).body_fat_pct ?? null,
        muscle_mass_kg: (body as any).muscle_mass_kg ?? null,
        update_date: (body as any).update_date ?? '',
      },
      sleep: {
        score: (sleep as any).score ?? null,
        total_hours: (sleep as any).total_hours ?? null,
        deep_sleep_percent: (sleep as any).deep_sleep_percent ?? null,
      },
      nutrition: {
        total_calories: (nutrition as any).total_calories ?? null,
        balance_score: (nutrition as any).balance_score ?? null,
      },
      exercise: {
        steps: (exercise as any).steps ?? null,
        steps_goal: (exercise as any).steps_goal ?? 8000,
        duration_minutes: (exercise as any).duration_minutes ?? null,
        calories_burned: (exercise as any).calories_burned ?? null,
        intensity: (exercise as any).intensity ?? '',
      },
      healthAdvice: {
        exercise: store.healthAdvice?.exercise || '每日30分钟有氧搭配15分钟力量，快走、哑铃皆可',
        sleep: store.healthAdvice?.sleep || '固定23点前入睡，每日睡7-8小时，睡前少看电子屏',
        nutrition: store.healthAdvice?.nutrition || '三餐粗细搭配，优质蛋白足量摄入，少油少盐控糖',
      },
    }
  }

  async function exportReportImage(): Promise<string | null> {
    isLoading.value = true
    errorMsg.value = null

    const data = buildReportData()
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 120000)

    try {
      const resp = await fetch('/api/report-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        signal: controller.signal,
      })
      clearTimeout(timeout)

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: `服务返回 ${resp.status}` }))
        throw new Error(err.error || `服务返回 ${resp.status}`)
      }

      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      return url
    } catch (e: any) {
      clearTimeout(timeout)
      if (e?.name === 'AbortError') {
        errorMsg.value = '生成超时，请稍后重试'
      } else {
        errorMsg.value = e?.message || '报告图片生成失败，请稍后重试'
      }
      return null
    } finally {
      isLoading.value = false
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

  return { isLoading, errorMsg, buildReportData, exportReportImage, downloadImage }
}
