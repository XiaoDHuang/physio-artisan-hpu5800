// 会话状态管理（Pinia）
//
// 会话列表从服务端拉取（GET /conversations），支持跨设备/跨浏览器。
// 切换某条会话时用 GET /conversations/{id} 拉取消息。

import { defineStore } from 'pinia'
import {
  sendChat,
  getConversation,
  deleteConversation,
  listConversations,
} from '@/api/chat'

export interface UIMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  // assistant 消息流式输出期间为 true
  streaming?: boolean
}

export interface ConversationMeta {
  id: string
  title: string
  updatedAt: number
}

let _uid = 0
function genId(): string {
  _uid += 1
  return `m_${Date.now()}_${_uid}`
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversations: [] as ConversationMeta[],
    // 当前选中的会话 id；null 表示「新会话」尚未在服务端建立
    activeId: null as string | null,
    messages: [] as UIMessage[],
    sending: false,
    listLoading: false,
    abortController: null as AbortController | null,
  }),

  getters: {
    // ant-design-x Conversations 组件需要的列表结构
    conversationItems(state) {
      return state.conversations.map((c) => ({ key: c.id, label: c.title }))
    },
  },

  actions: {
    // 从服务端拉取会话列表（左侧历史栏）
    async fetchConversations() {
      this.listLoading = true
      try {
        const list = await listConversations()
        this.conversations = list.map((c) => ({
          id: c.conversation_id,
          title: c.title || '新对话',
          updatedAt: c.updated_at,
        }))
      } catch {
        // 拉取失败保留现有列表，不阻断 UI
      } finally {
        this.listLoading = false
      }
    },

    // 开启一个全新的空会话（尚未在服务端创建，发首条消息时才有 id）
    newConversation() {
      this.activeId = null
      this.messages = []
    },

    // 切换到某个已存在的会话并拉取其历史
    async selectConversation(id: string) {
      if (this.sending) return
      this.activeId = id
      this.messages = []
      try {
        const resp = await getConversation(id)
        this.messages = resp.messages
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .map((m) => ({
            id: genId(),
            role: m.role as 'user' | 'assistant',
            content: m.content,
          }))
      } catch {
        // 拉取失败时保留空列表，不阻断 UI
      }
    },

    // 删除会话（服务端 + 本地列表）
    async removeConversation(id: string) {
      try {
        await deleteConversation(id)
      } catch {
        // 即使服务端删除失败，也从本地列表移除，避免残留
      }
      this.conversations = this.conversations.filter((c) => c.id !== id)
      if (this.activeId === id) this.newConversation()
    },

    // 发送消息并接收流式回复
    async send(text: string) {
      const content = text.trim()
      if (!content || this.sending) return

      this.sending = true
      this.abortController = new AbortController()

      this.messages.push({ id: genId(), role: 'user', content })
      this.messages.push({
        id: genId(),
        role: 'assistant',
        content: '',
        streaming: true,
      })
      // 取数组里的响应式引用来更新；直接改 push 进去的原始对象不会触发渲染
      const assistant = this.messages[this.messages.length - 1]

      const isNew = !this.activeId

      await sendChat(
        {
          message: content,
          conversationId: this.activeId ?? undefined,
          signal: this.abortController.signal,
        },
        {
          onConversationId: (id) => {
            this.activeId = id
            // 新会话：先乐观插入到列表顶部，标题取首条用户消息
            if (isNew && !this.conversations.some((c) => c.id === id)) {
              this.conversations.unshift({
                id,
                title: content.slice(0, 20) || '新对话',
                updatedAt: Date.now() / 1000,
              })
            }
          },
          onToken: (token) => {
            assistant.content += token
          },
          onError: (msg) => {
            assistant.content += assistant.content
              ? `\n\n[出错：${msg}]`
              : `[出错：${msg}]`
          },
        },
      )

      assistant.streaming = false
      this.sending = false
      this.abortController = null

      // 与服务端对齐：重新拉取列表（更新标题、时间戳、排序）
      await this.fetchConversations()
    },

    // 中止当前流式请求
    stop() {
      this.abortController?.abort()
      this.abortController = null
      this.sending = false
      const last = this.messages[this.messages.length - 1]
      if (last?.streaming) last.streaming = false
    },
  },
})
