<script setup lang="ts">
// 通用卡片壳：白底 / 圆角 / 阴影 / 可选标题。
// 本期睡眠监测、饮食监测等卡片用它做占位（不填充内容）。
defineProps<{
  title?: string
  more?: boolean // 是否显示"了解更多"
  minHeight?: number
}>()
</script>

<template>
  <section class="section-card" :style="minHeight ? { minHeight: minHeight + 'px' } : {}">
    <header v-if="title" class="card-head">
      <span class="card-title">{{ title }}</span>
      <span v-if="more" class="card-more">了解更多 ›</span>
    </header>
    <div class="card-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.section-card {
  background: var(--c-card-bg);
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(31, 45, 40, 0.06);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.card-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--c-text);
}
.card-more {
  font-size: 12px;
  color: var(--c-text-tertiary);
  cursor: pointer;
}
.card-body {
  flex: 1;
}
</style>
