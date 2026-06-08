// 对话接口封装：/chat（SSE 流式）、/conversations（查询/清空）
//
// 说明：
// - POST /chat 是 SSE 流，需用 fetch + ReadableStream 手动解析，
//   因为要发送 POST body（EventSource 只支持 GET）。
// - 流格式：每条以 "data: " 开头，可能是：
//     {"conversation_id": "..."}  首事件
//     {"content": "token"}        增量
//     [DONE]                      结束
//     {"error": "..."}            服务端错误

import type {
  ChatStreamHandlers,
  ConversationResponse,
  ConversationSummary,
} from './types'

// 统一前缀，开发期由 Vite 代理到 FastAPI(8000)
const BASE = '/api'

export interface SendChatParams {
  message: string
  conversationId?: string
  signal?: AbortSignal
}

/**
 * 发送一条消息并以 SSE 流式接收回复。
 * 返回一个 Promise，在流结束（或出错）后 resolve。
 */
export async function sendChat(
  params: SendChatParams,
  handlers: ChatStreamHandlers,
): Promise<void> {
  const { message, conversationId, signal } = params

  let resp: Response
  try {
    resp = await fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? null,
      }),
      signal,
    })
  } catch (e) {
    handlers.onError?.(e instanceof Error ? e.message : '网络请求失败')
    return
  }

  if (!resp.ok || !resp.body) {
    handlers.onError?.(`服务端返回异常：HTTP ${resp.status}`)
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE 事件以空行分隔；逐行解析以 data: 开头的内容
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? '' // 末行可能不完整，留到下次

      for (const raw of lines) {
        const line = raw.trim()
        if (!line.startsWith('data:')) continue
        const data = line.slice(5).trim()
        if (!data) continue

        if (data === '[DONE]') {
          handlers.onDone?.()
          return
        }

        try {
          const obj = JSON.parse(data)
          if (obj.conversation_id) handlers.onConversationId?.(obj.conversation_id)
          if (obj.content) handlers.onToken?.(obj.content)
          if (obj.error) handlers.onError?.(obj.error)
        } catch {
          // 非 JSON 行忽略
        }
      }
    }
    // 流自然结束但没收到 [DONE]，也视作完成
    handlers.onDone?.()
  } catch (e) {
    if ((e as Error)?.name === 'AbortError') return
    handlers.onError?.(e instanceof Error ? e.message : '读取流失败')
  }
}

/** 查询某个会话的历史消息 */
export async function getConversation(id: string): Promise<ConversationResponse> {
  const resp = await fetch(`${BASE}/conversations/${encodeURIComponent(id)}`)
  if (!resp.ok) throw new Error(`查询会话失败：HTTP ${resp.status}`)
  return resp.json()
}

/** 列出所有会话（按最近更新倒序） */
export async function listConversations(): Promise<ConversationSummary[]> {
  const resp = await fetch(`${BASE}/conversations`)
  if (!resp.ok) throw new Error(`查询会话列表失败：HTTP ${resp.status}`)
  return resp.json()
}

/** 清空（删除）某个会话的历史 */
export async function deleteConversation(id: string): Promise<void> {
  const resp = await fetch(`${BASE}/conversations/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  if (!resp.ok) throw new Error(`删除会话失败：HTTP ${resp.status}`)
}
