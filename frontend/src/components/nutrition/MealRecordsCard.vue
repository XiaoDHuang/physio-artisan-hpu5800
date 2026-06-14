<script setup lang="ts">
// 今日饮食记录：早/午/晚/加餐 分组 + 食物明细（名称/克数/热量）
import type { Meal } from '@/api/types'
import SectionCard from '@/components/report/SectionCard.vue'
import icBaozi from '@/assets/page-nutrition/包子.png'
import icMilk from '@/assets/page-nutrition/牛奶.png'
import icBroccoli from '@/assets/page-nutrition/西兰花.png'
import icChicken from '@/assets/page-nutrition/鸡胸肉.png'
import icEgg from '@/assets/page-nutrition/鸡蛋.png'

defineProps<{ meals: Meal[] }>()

const ICONS: Record<string, string> = {
  包子: icBaozi, 牛奶: icMilk, 西兰花: icBroccoli, 鸡胸肉: icChicken, 鸡蛋: icEgg,
}
function iconFor(name: string): string | null {
  if (ICONS[name]) return ICONS[name]
  const k = Object.keys(ICONS).find((key) => name.includes(key) || key.includes(name))
  return k ? ICONS[k] : null
}

const MEAL_COLOR: Record<string, string> = {
  早餐: '#5fb98f', 午餐: '#f5a623', 晚餐: '#9b8cf5', 加餐: '#e36a6a',
}
const dash = (v: number | null | undefined) => (v == null ? '—' : v)
</script>

<template>
  <SectionCard>
    <div class="head">
      <span class="title">今日饮食记录</span>
      <button class="add-btn" type="button">记录 +</button>
    </div>

    <div v-if="meals.length" class="meals">
      <div v-for="(m, i) in meals" :key="i" class="meal">
        <div class="meal-head">
          <span class="meal-dot" :style="{ background: MEAL_COLOR[m.meal_type] || '#9aa8a2' }" />
          <span class="meal-name">{{ m.meal_type }}</span>
          <span class="meal-time">{{ m.time }}</span>
          <span class="meal-cal">{{ dash(m.total_calories) }} 千卡</span>
        </div>
        <div class="foods">
          <div v-for="(f, j) in m.foods" :key="j" class="food">
            <div class="food-ic">
              <img v-if="iconFor(f.name)" :src="iconFor(f.name)!" :alt="f.name" />
              <span v-else class="ph">{{ f.name.slice(0, 1) }}</span>
            </div>
            <div class="food-name">{{ f.name }}</div>
            <div class="food-g">{{ dash(f.grams) }} g</div>
            <div class="food-cal">{{ dash(f.calories) }} 千卡</div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty">今日暂无饮食记录</div>
  </SectionCard>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.title {
  font-size: 16px;
  font-weight: 700;
  color: var(--c-text);
}
.add-btn {
  border: none;
  background: transparent;
  color: var(--c-primary-hover);
  font-size: 13px;
  cursor: pointer;
}
.meal {
  padding: 14px 0;
}
.meal + .meal {
  border-top: 1px solid var(--c-border);
}
.meal-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.meal-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.meal-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
}
.meal-time {
  font-size: 12px;
  color: var(--c-text-tertiary);
}
.meal-cal {
  margin-left: auto;
  font-size: 13px;
  color: var(--c-text-secondary);
  font-weight: 600;
}
.foods {
  display: flex;
  gap: 26px;
  flex-wrap: wrap;
  padding-left: 16px;
}
.food {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 64px;
  text-align: center;
}
.food-ic {
  width: 50px;
  height: 50px;
  border-radius: 12px;
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
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  margin-top: 6px;
}
.food-g {
  font-size: 11px;
  color: var(--c-text-tertiary);
  margin-top: 1px;
}
.food-cal {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text-secondary);
  margin-top: 1px;
}
.empty {
  padding: 30px 0;
  text-align: center;
  font-size: 13px;
  color: var(--c-text-tertiary);
}
</style>
