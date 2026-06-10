<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import logo from '@/assets/logo/logo.png'
import navReport from '@/assets/nav-bar/健康报告.png'

interface NavItem {
  name: string
  path: string
  label: string
  icon?: string // 图片图标（可选）
  emoji?: string // 兜底图标
}

// 顺序对齐设计图：运动分析 / 睡眠监测 / 饮食管理 / 健康报告(当前)
const items: NavItem[] = [
  { name: 'exercise', path: '/exercise', label: '运动分析', emoji: '🏃' },
  { name: 'sleep', path: '/sleep', label: '睡眠监测', emoji: '😴' },
  { name: 'nutrition', path: '/nutrition', label: '饮食管理', emoji: '🍽️' },
  { name: 'report', path: '/report', label: '健康报告', icon: navReport },
]

const route = useRoute()
const router = useRouter()

function go(item: NavItem) {
  if (route.path !== item.path) router.push(item.path)
}
</script>

<template>
  <aside class="side-nav">
    <div class="brand">
      <img :src="logo" alt="数建云" class="brand-logo" />
      <span class="brand-name">数建云</span>
    </div>

    <nav class="menu">
      <button
        v-for="item in items"
        :key="item.name"
        class="menu-item"
        :class="{ active: route.name === item.name }"
        @click="go(item)"
      >
        <img v-if="item.icon" :src="item.icon" class="menu-icon" alt="" />
        <span v-else class="menu-emoji">{{ item.emoji }}</span>
        <span class="menu-label">{{ item.label }}</span>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.side-nav {
  width: 208px;
  flex-shrink: 0;
  height: 100%;
  background: var(--c-sidebar-bg);
  border-right: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  padding: 18px 12px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px 18px;
}
.brand-logo {
  width: 32px;
  height: 32px;
  object-fit: contain;
}
.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--c-text);
  letter-spacing: 1px;
}
.menu {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 14px;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  font-size: 15px;
  color: var(--c-text-secondary);
  transition: all 0.15s ease;
  text-align: left;
}
.menu-item:hover {
  background: var(--c-primary-soft);
  color: var(--c-text);
}
.menu-item.active {
  background: var(--c-primary-soft);
  color: var(--c-primary-hover);
  font-weight: 600;
}
.menu-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
}
.menu-emoji {
  width: 20px;
  text-align: center;
  font-size: 16px;
}
</style>
