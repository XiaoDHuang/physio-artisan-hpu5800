<script setup lang="ts">
// 消息列表：用 ant-design-x 的 Bubble.List 渲染气泡
import { computed, h, nextTick, ref, watch } from 'vue'
import { Bubble } from 'ant-design-x-vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const listRef = ref<HTMLElement | null>(null)

// 角色样式：用户右侧主色气泡，助手左侧白底气泡
const roles = {
  user: {
    placement: 'end' as const,
    // TODO[icon]: 用户头像占位
    avatar: { style: { background: '#34a87c' }, icon: h('span', '我') },
    styles: {
      content: { background: 'var(--c-primary)', color: '#fff' },
    },
  },
  assistant: {
    placement: 'start' as const,
    // TODO[icon]: 助手头像占位
    avatar: { style: { background: 'var(--c-primary-soft)', color: 'var(--c-primary)' }, icon: h('span', 'AI') },
    // 打字机效果由 store 缓冲循环统一控制（见 stores/chat.ts），
    // 这里不再开 Bubble 自带 typing，避免双重动画。
    styles: {
      content: { background: '#fff', color: 'var(--c-text)' },
    },
  },
}

const bubbleItems = computed(() =>
  store.messages.map((m) => ({
    key: m.id,
    role: m.role,
    content: m.content,
    loading: m.role === 'assistant' && m.streaming && !m.content,
  })),
)

// 新消息或流式增量时自动滚到底部
watch(
  () => [store.messages.length, store.messages[store.messages.length - 1]?.content],
  async () => {
    await nextTick()
    const el = listRef.value
    if (el) el.scrollTop = el.scrollHeight
  },
)
</script>

<template>
  <div ref="listRef" class="msg-list">
    <Bubble.List :roles="roles" :items="bubbleItems" />
  </div>
</template>

<style scoped>
.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px clamp(16px, 8%, 120px);
}
:deep(.ant-bubble) {
  margin-bottom: 18px;
}
</style>
