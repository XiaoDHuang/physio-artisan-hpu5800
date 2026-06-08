<script setup lang="ts">
// 左侧历史会话栏：新建按钮 + 会话列表（从服务端拉取）
import { computed, onMounted } from 'vue'
import { Conversations } from 'ant-design-x-vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()

// 进入页面即从服务端拉取会话列表
onMounted(() => {
  store.fetchConversations()
})

const items = computed(() =>
  store.conversations.map((c) => ({ key: c.id, label: c.title })),
)

const activeKey = computed(() => store.activeId ?? undefined)

function onActiveChange(key: string) {
  store.selectConversation(key)
}

// 每条会话的「更多」菜单：删除
const menuConfig = (conversation: { key: string }) => ({
  items: [
    {
      // TODO[icon]: 删除图标占位
      label: '删除',
      key: 'delete',
      danger: true,
    },
  ],
  onClick: ({ key: menuKey }: { key: string | number }) => {
    if (menuKey === 'delete') store.removeConversation(conversation.key)
  },
})
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar__brand">
      <!-- TODO[icon]: 品牌 Logo 占位 -->
      <span class="sidebar__logo">◎</span>
      <span class="sidebar__title">健身训练助手</span>
    </div>

    <a-button class="sidebar__new" type="primary" block @click="store.newConversation">
      <!-- TODO[icon]: 新建图标占位 -->
      <span class="sidebar__new-plus">＋</span>
      新对话
    </a-button>

    <div class="sidebar__list">
      <Conversations
        v-if="items.length"
        :items="items"
        :active-key="activeKey"
        :menu="menuConfig"
        @active-change="onActiveChange"
      />
      <div v-else class="sidebar__empty">暂无历史对话</div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 280px;
  flex-shrink: 0;
  height: 100%;
  background: var(--c-sidebar-bg);
  border-right: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  gap: 14px;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px;
}
.sidebar__logo {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: var(--c-primary-soft);
  color: var(--c-primary);
  font-size: 18px;
}
.sidebar__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text);
}

.sidebar__new {
  height: 40px;
  border-radius: 10px;
  font-weight: 500;
}
.sidebar__new-plus {
  margin-right: 6px;
  font-size: 16px;
}

.sidebar__list {
  flex: 1;
  overflow-y: auto;
  margin: 0 -4px;
}

.sidebar__empty {
  text-align: center;
  color: var(--c-text-tertiary);
  font-size: 13px;
  padding-top: 40px;
}
</style>
