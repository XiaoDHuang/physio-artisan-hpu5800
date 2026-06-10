// 底部聊天框状态（Pinia）— 单轮问答、覆盖式
//
// 需求（docs/frontend/design.md §6）：
// - 只显示当前一问一答；输入框下方只显示最新机器人回答，再次输入即覆盖。
// - 用临时 conversation_id（仅内存）：首次为空 → 后端创建并回传；丢失则重建。

import { defineStore } from 'pinia'
import { postChat } from '@/api/chat'
import type { ChatIntent } from '@/api/types'

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversationId: null as string | null,
    sending: false,
    lastQuestion: '' as string,
    lastReply: '' as string,
    lastIntent: '' as ChatIntent | '',
  }),

  actions: {
    async send(text: string) {
      const msg = text.trim()
      if (!msg || this.sending) return
      this.sending = true
      this.lastQuestion = msg
      this.lastReply = ''
      try {
        const resp = await postChat({ message: msg, conversation_id: this.conversationId })
        // 首次会创建临时会话ID；后续沿用，丢失则后端再建一个
        this.conversationId = resp.conversation_id
        this.lastReply = resp.reply
        this.lastIntent = resp.intent
      } catch (e) {
        this.lastReply = `出错了：${e instanceof Error ? e.message : '请求失败'}`
        this.lastIntent = ''
      } finally {
        this.sending = false
      }
    },

    reset() {
      this.conversationId = null
      this.lastQuestion = ''
      this.lastReply = ''
      this.lastIntent = ''
    },
  },
})
