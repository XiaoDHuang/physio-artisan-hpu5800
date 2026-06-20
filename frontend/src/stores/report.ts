// 报告 / 看板数据状态（Pinia）
//
// 取数策略（见 docs/frontend/design.md §5）：
//   1) GET /dashboard/{uid}?date=  看板指标（可按日期切换锚点）
//   2) GET /report/latest/{uid}    健康建议文案（有缓存则附带）

import { defineStore } from 'pinia'
import { getDashboard, getLatestReport } from '@/api/report'
import type { Dashboard, ReportResult } from '@/api/types'
import type { HttpError } from '@/api/http'
import { useUserStore } from '@/stores/user'

function shiftDate(dateStr: string, delta: number): string {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setDate(d.getDate() + delta)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function todayLocal(): string {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

export const useReportStore = defineStore('report', {
  state: () => ({
    dashboard: null as Dashboard | null,
    result: null as ReportResult | null,
    hasReport: false,
    date: '' as string,
    loading: false,
    error: '' as string,
  }),

  getters: {
    kpi: (s) => s.dashboard?.kpi ?? null,
    body: (s) => s.dashboard?.body_overview ?? null,
    sleep: (s) => s.dashboard?.sleep ?? null,
    nutrition: (s) => s.dashboard?.nutrition ?? null,
    exerciseToday: (s) => s.dashboard?.exercise_today ?? null,
    weekSummary: (s) => s.dashboard?.week_summary ?? null,
    healthAdvice: (s) => {
      const anchor = s.result?.anchor_date
      if (anchor && s.date && anchor !== s.date) return null
      if (!s.hasReport) return null
      const cards = s.result?.final_report?.chart_data?.cards as
        | { health_advice?: { exercise: string; sleep: string; nutrition: string } }
        | undefined
      return cards?.health_advice ?? null
    },
    isToday: (s) => !s.date || s.date >= todayLocal(),
    /** 当前看板日已有 AI 报告缓存时可导出图片 */
    canExportReport: (s) => s.hasReport && !s.loading && Boolean(s.date),
  },

  actions: {
    async load(date?: string, userId?: number) {
      const uid = userId ?? useUserStore().userId
      if (date !== undefined) this.date = date
      this.loading = true
      this.error = ''
      this.dashboard = null
      this.result = null
      this.hasReport = false
      try {
        const d = await getDashboard(uid, this.date || undefined)
        this.dashboard = d.dashboard
        this.date = d.date

        try {
          const r = await getLatestReport(uid, this.date || undefined)
          this.result = r
          this.hasReport = true
        } catch (e) {
          if ((e as HttpError)?.status === 404) {
            this.hasReport = false
          } else {
            throw e
          }
        }
      } catch (e) {
        this.error = e instanceof Error ? e.message : '加载失败'
      } finally {
        this.loading = false
      }
    },

    prevDay() {
      if (this.date) this.load(shiftDate(this.date, -1))
    },

    nextDay() {
      if (!this.date) return
      const next = shiftDate(this.date, 1)
      if (next > todayLocal()) return
      this.load(next)
    },
  },
})
