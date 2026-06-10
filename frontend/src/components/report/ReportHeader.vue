<script setup lang="ts">
// 标题头：标题 + 占位 pill/按钮（不交互）+ 右侧日期与问候
import { computed } from 'vue'

// 右侧日期（动态取今天）：2026年6月3日 星期三
const WEEK = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const todayText = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${WEEK[d.getDay()]}`
})

// 占位日期（静态，不交互）
const dataTag = '2026-06-01健康数据'
const pickedDate = '2026 - 06 - 01'
const userName = 'Kevin'
</script>

<template>
  <header class="report-header">
    <!-- 左：标题 + 占位 pill + 导出按钮 -->
    <div class="left">
      <h1 class="title">健康报告</h1>

      <span class="pill">{{ dataTag }}</span>

      <span class="pill pill-date">
        <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
        {{ pickedDate }}
      </span>

      <button class="export-btn" disabled>
        <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        导出报告
      </button>
    </div>

    <!-- 右：日期 + 问候 + 头像 -->
    <div class="right">
      <div class="date-info">
        <div class="today">{{ todayText }}</div>
        <div class="greeting">Hello {{ userName }}</div>
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
.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.title {
  margin: 0;
  color: #3d3d3d;
  font-size: 24px;
  font-weight: 500;
  font-family: 'Source Han Sans', 'Source Han Sans SC', 'Noto Sans CJK SC',
    'PingFang SC', 'Microsoft YaHei', sans-serif;
  white-space: nowrap;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 14px;
  background: #f3f5f7;
  border-radius: 8px;
  font-size: 13px;
  color: #5f6b66;
  white-space: nowrap;
  cursor: default;
}
.pill-date {
  color: #3d3d3d;
}
.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 16px;
  border: none;
  border-radius: 8px;
  background: var(--c-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: default;
  white-space: nowrap;
}
.ico {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}
.right {
  display: flex;
  align-items: center;
  gap: 12px;
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
