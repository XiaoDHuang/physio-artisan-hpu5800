<script setup lang="ts">
// 顶部 Banner：设计已是完整成品图（含标语/按钮/插画），整图展示即可
import bannerBg from '@/assets/page-exercise/banner-bg.png'
</script>

<template>
  <section class="banner">
    <img :src="bannerBg" class="banner-img" alt="健身正当时" />
  </section>
</template>

<style scoped>
.banner {
  width: 100%;
  border-radius: 18px;
  overflow: hidden;
  line-height: 0;
}
.banner-img {
  width: 100%;
  height: auto;
  display: block;
  object-fit: cover;
}
</style>
