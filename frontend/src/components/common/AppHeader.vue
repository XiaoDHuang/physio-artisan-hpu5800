<script setup lang="ts">
// 四页共用顶部 Header：左=标题(缺省取 route.meta.title) / 中=页面自定义槽位 / 右=当前日期+问候+头像
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps<{ title?: string; subtitle?: string }>()

// 本期无用户态，用户名取共享常量（设计图为 Kevin）
const USER_NAME = 'Kevin'

const route = useRoute()
const pageTitle = computed(() => props.title || (route.meta.title as string) || '')

const WEEK = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const todayText = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${WEEK[d.getDay()]}`
})
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
        <div class="greeting">Hello {{ USER_NAME }}</div>
      </div>
      <div class="avatar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
             stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
        </svg>
      </div>
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
.avatar svg {
  width: 22px;
  height: 22px;
}
</style>
