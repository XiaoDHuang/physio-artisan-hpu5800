<script setup lang="ts">
import { ConfigProvider } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import AppLayout from '@/layouts/AppLayout.vue'
import { antdThemeToken } from '@/theme'
</script>

<template>
  <ConfigProvider :locale="zhCN" :theme="{ token: antdThemeToken }">
    <AppLayout />
  </ConfigProvider>
</template>
