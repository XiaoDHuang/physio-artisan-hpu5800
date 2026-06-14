// 睡眠监测页状态（Pinia）：取数 + 趋势区间 + 录入回刷
import { defineStore } from 'pinia'
import { getSleep, postSleepEntry, type SleepRangeOpt } from '@/api/sleep'
import type { SleepPage, SleepEntryPayload, SourceMap } from '@/api/types'
import type { HttpError } from '@/api/http'

export const USER_ID = 1

export const useSleepStore = defineStore('sleep', {
  state: () => ({
    data: null as SleepPage | null,
    sources: {} as SourceMap,
    range: '7d' as SleepRangeOpt,
    loading: false,
    saving: false,
    error: '' as string,
  }),

  getters: {
    today: (s) => s.data?.today ?? null,
    duration: (s) => s.data?.duration ?? null,
    nap: (s) => s.data?.nap ?? null,
    trend: (s) => s.data?.trend ?? [],
    advice: (s) => s.data?.advice ?? null,
    foods: (s) => s.data?.foods ?? null,
  },

  actions: {
    async load(range?: SleepRangeOpt, userId: number = USER_ID) {
      if (range) this.range = range
      this.loading = true
      this.error = ''
      try {
        const r = await getSleep(userId, this.range)
        this.data = r.sleep
        this.sources = r.sources || {}
      } catch (e) {
        this.error = (e as HttpError)?.message || '加载失败'
      } finally {
        this.loading = false
      }
    },

    /** 录入睡眠时间，成功后回刷本页 */
    async saveEntry(payload: SleepEntryPayload, userId: number = USER_ID): Promise<boolean> {
      this.saving = true
      try {
        const r = await postSleepEntry({ ...payload, user_id: payload.user_id ?? userId })
        if (r.saved) await this.load(undefined, userId)
        return !!r.saved
      } catch (e) {
        this.error = (e as HttpError)?.message || '保存失败'
        return false
      } finally {
        this.saving = false
      }
    },
  },
})
