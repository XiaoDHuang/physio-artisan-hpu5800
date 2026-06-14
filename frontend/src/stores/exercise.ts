// 运动分析页状态（Pinia）：取数 + 分块 getters，沿用 report.ts 模式
import { defineStore } from 'pinia'
import { getExercise } from '@/api/exercise'
import type { ExercisePage, SourceMap } from '@/api/types'
import type { HttpError } from '@/api/http'

// 暂无用户态，固定演示用户
export const USER_ID = 1

export const useExerciseStore = defineStore('exercise', {
  state: () => ({
    data: null as ExercisePage | null,
    sources: {} as SourceMap,
    loading: false,
    error: '' as string,
  }),

  getters: {
    overview: (s) => s.data?.today_overview ?? null,
    status: (s) => s.data?.today_status ?? null,
    records: (s) => s.data?.today_records ?? [],
    weekTrend: (s) => s.data?.week_trend ?? [],
    advice: (s) => s.data?.advice ?? null,
    achievement: (s) => s.data?.achievement ?? null,
  },

  actions: {
    async load(userId: number = USER_ID) {
      this.loading = true
      this.error = ''
      try {
        const r = await getExercise(userId)
        this.data = r.exercise
        this.sources = r.sources || {}
      } catch (e) {
        this.error = (e as HttpError)?.message || '加载失败'
      } finally {
        this.loading = false
      }
    },
  },
})
