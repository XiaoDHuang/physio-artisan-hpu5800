<script setup lang="ts">
// 右侧 Agent 聊天面板：欢迎区/消息区 + 底部输入区
// 底部输入区 UI 参考背景色调.jpg 右下：
//   顶部一行建议气泡 + 多行输入框 + 底部工具行（图片识别/视频上传/语音）
import { ref } from 'vue'
import { Sender, Prompts } from 'ant-design-x-vue'
import MessageList from './MessageList.vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const inputValue = ref('')

// 欢迎区建议（参考图底部的快捷问题）
const suggestions = [
  { key: 's1', description: '如何提升睡眠质量？' },
  { key: 's2', description: '适合我的减脂计划是什么？' },
  { key: 's3', description: '今天的运动目标怎么设定？' },
]

function handleSubmit(text: string) {
  const content = (text ?? inputValue.value).trim()
  if (!content) return
  inputValue.value = ''
  store.send(content)
}

function handleSuggestion(info: { data: { description?: unknown } }) {
  const text = info.data.description
  if (typeof text === 'string') handleSubmit(text)
}
</script>

<template>
  <section class="panel">
    <header class="panel__header">
      <div class="panel__title">
        <!-- TODO[icon]: 助手图标占位 -->
        <span class="panel__bot">🤖</span>
        <div>
          <div class="panel__name">健身训练助手</div>
          <div class="panel__desc">您的智能健身训练助手</div>
        </div>
      </div>
    </header>

    <!-- 空会话：欢迎区；有消息：消息列表 -->
    <div v-if="!store.messages.length" class="panel__welcome">
      <div class="welcome__icon">🤖</div>
      <div class="welcome__greet">Hi！我是你的健身训练助手，有什么可以帮你的吗？</div>
      <Prompts
        class="welcome__prompts"
        :items="suggestions"
        wrap
        @item-click="handleSuggestion"
      />
    </div>
    <MessageList v-else />

    <!-- 底部输入区 -->
    <footer class="panel__input">
      <Sender
        v-model:value="inputValue"
        placeholder="发消息"
        :loading="store.sending"
        :auto-size="{ minRows: 2, maxRows: 6 }"
        @submit="handleSubmit"
        @cancel="store.stop"
      >
        <template #footer>
          <div class="input-toolbar">
            <div class="input-toolbar__left">
              <!-- TODO[icon]: 以下均为占位图标，待替换 -->
              <button class="tool-btn" type="button" title="添加">＋</button>
              <span class="tool-divider" />
              <button class="tool-btn" type="button">▦ 图片识别</button>
              <button class="tool-btn" type="button">▷ 视频上传</button>
            </div>
            <div class="input-toolbar__right">
              <button class="tool-btn" type="button" title="语音">🎤</button>
            </div>
          </div>
        </template>
      </Sender>
    </footer>
  </section>
</template>

<style scoped>
.panel {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--c-panel-bg);
  min-width: 0;
}

.panel__header {
  height: 60px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0 24px;
  border-bottom: 1px solid var(--c-border);
  background: var(--c-card-bg);
}
.panel__title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.panel__bot {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  font-size: 22px;
  border-radius: 10px;
  background: var(--c-primary-soft);
}
.panel__name {
  font-size: 15px;
  font-weight: 600;
}
.panel__desc {
  font-size: 12px;
  color: var(--c-text-secondary);
}

.panel__welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 24px;
}
.welcome__icon {
  font-size: 64px;
}
.welcome__greet {
  font-size: 16px;
  color: var(--c-text);
}
.welcome__prompts {
  max-width: 720px;
}

.panel__input {
  flex-shrink: 0;
  padding: 12px 24px 20px;
}

.input-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 6px;
}
.input-toolbar__left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tool-btn {
  border: none;
  background: transparent;
  color: var(--c-text-secondary);
  cursor: pointer;
  font-size: 13px;
  padding: 4px 6px;
  border-radius: 6px;
}
.tool-btn:hover {
  background: var(--c-primary-soft);
  color: var(--c-primary);
}
.tool-divider {
  width: 1px;
  height: 16px;
  background: var(--c-border);
}
</style>
