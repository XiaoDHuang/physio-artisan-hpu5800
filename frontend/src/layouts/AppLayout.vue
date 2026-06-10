<script setup lang="ts">
import SideNav from '@/components/nav/SideNav.vue'
</script>

<template>
  <div class="app-layout">
    <SideNav />
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  width: 100%;
  height: 100%;
}
.app-main {
  flex: 1;
  height: 100%;
  overflow: hidden;
  background: var(--c-app-bg);
}
</style>
