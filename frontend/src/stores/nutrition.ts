// 饮食管理页状态（Pinia）：取数 + 日期前后切换
import { defineStore } from 'pinia'
import { getNutrition } from '@/api/nutrition'
import type { NutritionPage, SourceMap } from '@/api/types'
import type { HttpError } from '@/api/http'

export const USER_ID = 1

// 'YYYY-MM-DD' 加减天数（本地时区）
function shiftDate(dateStr: string, delta: number): string {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setDate(d.getDate() + delta)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

export const useNutritionStore = defineStore('nutrition', {
  state: () => ({
    data: null as NutritionPage | null,
    date: '' as string,
    sources: {} as SourceMap,
    loading: false,
    error: '' as string,
  }),

  getters: {
    kpi: (s) => s.data?.kpi ?? null,
    energy: (s) => s.data?.energy ?? null,
    meals: (s) => s.data?.meals ?? [],
    exerciseAdvice: (s) => s.data?.exercise_advice ?? null,
  },

  actions: {
    async load(date?: string, userId: number = USER_ID) {
      if (date !== undefined) this.date = date
      this.loading = true
      this.error = ''
      try {
        const r = await getNutrition(userId, this.date || undefined)
        this.data = r.nutrition
        this.sources = r.sources || {}
        this.date = r.date // 回显后端实际日期（缺省时取今天）
      } catch (e) {
        this.error = (e as HttpError)?.message || '加载失败'
      } finally {
        this.loading = false
      }
    },
    prevDay() {
      if (this.date) this.load(shiftDate(this.date, -1))
    },
    nextDay() {
      if (this.date) this.load(shiftDate(this.date, 1))
    },
  },
})
