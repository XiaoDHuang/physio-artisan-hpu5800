// 路由表：健康报告（实现）+ 运动分析/睡眠监测/饮食管理（占位）
// 全部在 AppLayout 下切换右侧 <RouterView/>。

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/report' },
  {
    path: '/report',
    name: 'report',
    component: () => import('@/views/ReportView.vue'),
    meta: { title: '健康报告' },
  },
  {
    path: '/exercise',
    name: 'exercise',
    component: () => import('@/views/ExerciseView.vue'),
    meta: { title: '运动分析' },
  },
  {
    path: '/sleep',
    name: 'sleep',
    component: () => import('@/views/SleepView.vue'),
    meta: { title: '睡眠监测' },
  },
  {
    path: '/nutrition',
    name: 'nutrition',
    component: () => import('@/views/NutritionView.vue'),
    meta: { title: '饮食管理' },
  },
  { path: '/:pathMatch(.*)*', redirect: '/report' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
