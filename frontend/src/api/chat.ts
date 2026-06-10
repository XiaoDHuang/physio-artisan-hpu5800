// 对话接口：POST /chat 现为一次性结构化 JSON（非 SSE）。
import { postJson } from './http'
import type { ChatResponse } from './types'

export interface PostChatParams {
  message: string
  conversation_id?: string | null
}

/** 发送一条消息，返回结构化 ChatResponse（含 intent / reply / conversation_id 等）。 */
export function postChat(params: PostChatParams): Promise<ChatResponse> {
  return postJson<ChatResponse>('/chat', {
    message: params.message,
    conversation_id: params.conversation_id ?? null,
  })
}
