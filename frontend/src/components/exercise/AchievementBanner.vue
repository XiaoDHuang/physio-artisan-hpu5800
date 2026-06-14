<script setup lang="ts">
// 成就横幅：奖杯 + 超越百分比
import type { ExerciseAchievement } from '@/api/types'
import iconTrophy from '@/assets/page-exercise/继续保持.png'

defineProps<{ achievement: ExerciseAchievement | null }>()
</script>

<template>
  <section class="achievement">
    <img :src="iconTrophy" class="trophy" alt="" />
    <div class="text">
      <div class="title">继续保持！</div>
      <div class="desc">
        <template v-if="achievement?.percentile != null">
          你已超越了 <span class="hl">{{ achievement.percentile }}%</span> 的用户，加油，明天会更好！
        </template>
        <template v-else>{{ achievement?.description || '继续加油！' }}</template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.achievement {
  display: flex;
  align-items: center;
  gap: 18px;
  background: var(--c-primary-soft);
  border-radius: 16px;
  padding: 18px 26px;
}
.trophy {
  width: 56px;
  height: 56px;
  object-fit: contain;
  flex-shrink: 0;
}
.title {
  font-size: 16px;
  font-weight: 700;
  color: var(--c-primary-hover);
  margin-bottom: 4px;
}
.desc {
  font-size: 13px;
  color: var(--c-text-secondary);
}
.hl {
  color: var(--c-primary-hover);
  font-weight: 700;
}
</style>
