<script setup lang="ts">
// 四页共用顶部 Header：左=标题(缺省取 route.meta.title) / 中=页面自定义槽位 / 右=当前日期+问候+头像(可切换演示用户)
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { DEMO_USERS, useUserStore, type DemoUserId } from '@/stores/user'

const props = defineProps<{ title?: string; subtitle?: string }>()

const route = useRoute()
const userStore = useUserStore()
const { userId, userName, reloading } = storeToRefs(userStore)

const pageTitle = computed(() => props.title || (route.meta.title as string) || '')

const WEEK = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const todayText = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${WEEK[d.getDay()]}`
})

const userMenuItems = computed(() =>
  DEMO_USERS.map((u) => ({
    key: String(u.id),
    label: u.id === userId.value ? `${u.name}（当前）` : u.name,
    disabled: u.id === userId.value,
  })),
)

async function onUserMenuClick({ key }: { key: string }) {
  const id = Number(key) as DemoUserId
  if (id !== 1 && id !== 2) return
  await userStore.switchUser(id)
}
</script>

<template>
  <header class="app-header">
    <div class="left">
      <h1 class="title">{{ pageTitle }}</h1>
      <div v-if="subtitle" class="subtitle">{{ subtitle }}</div>
    </div>

    <div class="middle">
      <slot />
    </div>

    <div class="right">
      <div class="date-info">
        <div class="today">{{ todayText }}</div>
        <div class="greeting">Hello {{ userName }}</div>
      </div>
      <a-dropdown :trigger="['click']" placement="bottomRight">
        <button type="button" class="avatar user-switch" :class="{ loading: reloading }" title="切换用户" :disabled="reloading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
               stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
          </svg>
        </button>
        <template #overlay>
          <a-menu :items="userMenuItems" @click="onUserMenuClick" />
        </template>
      </a-dropdown>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
}
.left {
  flex-shrink: 0;
}
.title {
  margin: 0;
  color: #3d3d3d;
  font-size: 24px;
  font-weight: 600;
  white-space: nowrap;
}
.subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--c-text-tertiary);
  white-space: nowrap;
}
.middle {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  margin-left: 20px;
  min-width: 0;
}
.right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.date-info {
  text-align: right;
  line-height: 1.4;
}
.today {
  font-size: 13px;
  color: #3d3d3d;
}
.greeting {
  font-size: 12px;
  color: var(--c-text-tertiary);
}
.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--c-primary-soft);
  color: var(--c-primary-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.user-switch {
  border: none;
  padding: 0;
  cursor: pointer;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}
.user-switch:hover {
  box-shadow: 0 0 0 2px var(--c-primary-soft);
}
.user-switch:active:not(:disabled) {
  transform: scale(0.96);
}
.user-switch:disabled {
  opacity: 0.65;
  cursor: wait;
}
.user-switch.loading {
  animation: pulse 0.8s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.55; }
}
.avatar svg {
  width: 22px;
  height: 22px;
}
</style>
