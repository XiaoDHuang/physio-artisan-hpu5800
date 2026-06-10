<script setup lang="ts">
// 运动分析（占位）：右侧内容空白，仅演示路由跳转
</script>

<template>
  <div class="placeholder-view">
    <div class="empty">
      <div class="emoji">🏃</div>
      <div class="title">运动分析</div>
      <div class="desc">功能建设中…</div>
    </div>
  </div>
</template>

<style scoped>
.placeholder-view {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty {
  text-align: center;
  color: var(--c-text-tertiary);
}
.emoji {
  font-size: 48px;
}
.title {
  font-size: 20px;
  font-weight: 700;
  color: var(--c-text-secondary);
  margin-top: 12px;
}
.desc {
  margin-top: 6px;
  font-size: 14px;
}
</style>
