// 演示用户切换（user=1 小明 / user=2 小强），供 Header 与各页 Pinia 取数共用
import { defineStore } from 'pinia'

export const DEMO_USERS = [
  { id: 1, name: '小明' },
  { id: 2, name: '小强' },
] as const

export type DemoUserId = (typeof DEMO_USERS)[number]['id']

const STORAGE_KEY = 'hpu-demo-user-id'

function readStoredUserId(): DemoUserId {
  const raw = localStorage.getItem(STORAGE_KEY)
  const n = raw ? Number(raw) : 1
  return n === 2 ? 2 : 1
}

export const useUserStore = defineStore('user', {
  state: () => ({
    userId: readStoredUserId(),
    /** 每次切换用户 +1，供页面 watch 触发局部刷新 */
    reloadVersion: 0,
    reloading: false,
  }),

  getters: {
    userName: (s) => DEMO_USERS.find((u) => u.id === s.userId)?.name ?? `用户${s.userId}`,
  },

  actions: {
    async switchUser(id: DemoUserId) {
      if (this.userId === id) return
      this.userId = id
      localStorage.setItem(STORAGE_KEY, String(id))
      this.reloadVersion += 1

      const { useChatStore } = await import('./chat')
      useChatStore().reset()

      await this.reloadAllStores()
    },

    /** 切换用户后刷新四页 Pinia 缓存（并行请求） */
    async reloadAllStores() {
      this.reloading = true
      try {
        const [
          { useReportStore },
          { useExerciseStore },
          { useSleepStore },
          { useNutritionStore },
        ] = await Promise.all([
          import('./report'),
          import('./exercise'),
          import('./sleep'),
          import('./nutrition'),
        ])
        await Promise.all([
          useReportStore().load(),
          useExerciseStore().load(),
          useSleepStore().load(),
          useNutritionStore().load(),
        ])
      } finally {
        this.reloading = false
      }
    },
  },
})
