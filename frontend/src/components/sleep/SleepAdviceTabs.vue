<script setup lang="ts">
// 个性化建议：睡眠/饮食/运动 分页签 + 推荐/避免食物清单
import { ref, computed } from 'vue'
import type { SleepAdvice, SleepFoods } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import icBanana from '@/assets/page-sleep/香蕉.png'
import icOat from '@/assets/page-sleep/燕麦.png'
import icEgg from '@/assets/page-sleep/鸡蛋.png'
import icMilk from '@/assets/page-sleep/牛奶.png'
import icNut from '@/assets/page-sleep/坚果.png'
import icCoffee from '@/assets/page-sleep/咖啡.png'
import icSpicy from '@/assets/page-sleep/辛辣食物.png'
import icFried from '@/assets/page-sleep/油炸食品.png'
import icDessert from '@/assets/page-sleep/甜点.png'
import icMilktea from '@/assets/page-sleep/奶茶.png'

const props = defineProps<{ advice: SleepAdvice | null; foods: SleepFoods | null }>()

const TABS = [
  { key: 'sleep', label: '睡眠' },
  { key: 'nutrition', label: '饮食' },
  { key: 'exercise', label: '运动' },
] as const
type TabKey = (typeof TABS)[number]['key']
const active = ref<TabKey>('sleep')

const adviceText = computed(() => props.advice?.[active.value] || '暂无建议')

// 食物名 → 图标（精确 + 包含匹配；无图标则用首字占位）
const ICONS: Record<string, string> = {
  香蕉: icBanana, 燕麦: icOat, 鸡蛋: icEgg, 牛奶: icMilk, 坚果: icNut,
  咖啡: icCoffee, 辛辣食物: icSpicy, 油炸食品: icFried, 甜点: icDessert, 奶茶: icMilktea,
}
function iconFor(name: string): string | null {
  if (ICONS[name]) return ICONS[name]
  const k = Object.keys(ICONS).find((key) => name.includes(key) || key.includes(name))
  return k ? ICONS[k] : null
}
</script>

<template>
  <SectionCard title="个性化建议">
    <div class="tabs">
      <button
        v-for="t in TABS"
        :key="t.key"
        class="tab"
        :class="{ active: active === t.key }"
        @click="active = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <p class="advice">{{ adviceText }}</p>

    <div v-if="foods" class="foods">
      <div class="food-group">
        <div class="group-title rec">推荐食物</div>
        <div class="food-list">
          <div v-for="(f, i) in foods.recommended" :key="'r' + i" class="food">
            <div class="food-ic">
              <img v-if="iconFor(f)" :src="iconFor(f)!" :alt="f" />
              <span v-else class="ph">{{ f.slice(0, 1) }}</span>
            </div>
            <span class="food-name">{{ f }}</span>
          </div>
        </div>
      </div>
      <div class="food-group">
        <div class="group-title avoid">避免食物</div>
        <div class="food-list">
          <div v-for="(f, i) in foods.avoid" :key="'a' + i" class="food">
            <div class="food-ic">
              <img v-if="iconFor(f)" :src="iconFor(f)!" :alt="f" />
              <span v-else class="ph">{{ f.slice(0, 1) }}</span>
            </div>
            <span class="food-name">{{ f }}</span>
          </div>
        </div>
      </div>
    </div>
  </SectionCard>
</template>

<style scoped>
.tabs {
  display: inline-flex;
  gap: 4px;
  background: #f3f5f7;
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 14px;
}
.tab {
  border: none;
  background: transparent;
  padding: 6px 20px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--c-text-secondary);
  cursor: pointer;
}
.tab.active {
  background: #fff;
  color: var(--c-primary-hover);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(31, 45, 40, 0.08);
}
.advice {
  margin: 0 0 18px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--c-text-secondary);
}
.food-group + .food-group {
  margin-top: 16px;
}
.group-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
}
.group-title.rec {
  color: var(--c-primary-hover);
}
.group-title.avoid {
  color: #d65a5a;
}
.food-list {
  display: flex;
  gap: 22px;
  flex-wrap: wrap;
}
.food {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 56px;
}
.food-ic {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #f7faf9;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.food-ic img {
  width: 40px;
  height: 40px;
  object-fit: contain;
}
.ph {
  font-size: 18px;
  color: var(--c-text-tertiary);
}
.food-name {
  font-size: 12px;
  color: var(--c-text-secondary);
}
</style>
