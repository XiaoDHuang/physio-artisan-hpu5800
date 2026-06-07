<script setup lang="ts">
import { ConfigProvider } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import ChatSidebar from '@/components/ChatSidebar.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import { antdThemeToken } from '@/theme'
</script>

<template>
  <ConfigProvider :locale="zhCN" :theme="{ token: antdThemeToken }">
    <div class="layout">
      <ChatSidebar />
      <ChatPanel />
    </div>
  </ConfigProvider>
</template>

<style scoped>
.layout {
  display: flex;
  width: 100%;
  height: 100%;
}
</style>
