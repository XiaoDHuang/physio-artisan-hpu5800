// 报告 / 看板数据状态（Pinia）
//
// 取数策略（见 docs/frontend/design.md §5）：
//   1) GET /report/latest/{uid}  有报告 → 取 final_report.chart_data.dashboard
//   2) 404 → GET /dashboard/{uid} 仅看板
// 本期只对外提供 kpi / body 两块绑定。

import { defineStore } from 'pinia'
import { getDashboard, getLatestReport } from '@/api/report'
import type { Dashboard, ReportResult } from '@/api/types'
import type { HttpError } from '@/api/http'

// 暂无用户态，固定演示用户
export const USER_ID = 1

export const useReportStore = defineStore('report', {
  state: () => ({
    dashboard: null as Dashboard | null,
    result: null as ReportResult | null, // 完整报告（供后续 LLM 卡片填充）
    hasReport: false,
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
    // 健康建议三卡文本：仅当已有报告时存在（取 chart_data.cards.health_advice）
    healthAdvice: (s) => {
      const cards = s.result?.final_report?.chart_data?.cards as
        | { health_advice?: { exercise: string; sleep: string; nutrition: string } }
        | undefined
      return cards?.health_advice ?? null
    },
  },

  actions: {
    async load(userId: number = USER_ID) {
      this.loading = true
      this.error = ''
      try {
        try {
          const r = await getLatestReport(userId)
          this.result = r
          this.hasReport = true
          this.dashboard = r?.final_report?.chart_data?.dashboard ?? null
          // 报告里若未带 dashboard，则回退看板接口补齐
          if (!this.dashboard) {
            const d = await getDashboard(userId)
            this.dashboard = d.dashboard
          }
        } catch (e) {
          if ((e as HttpError)?.status === 404) {
            const d = await getDashboard(userId)
            this.dashboard = d.dashboard
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
  },
})
