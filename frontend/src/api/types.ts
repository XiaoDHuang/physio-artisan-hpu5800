// 与 backend FastAPI 对话相关的类型定义

export type Role = 'user' | 'assistant' | 'system'

export interface ChatMessageDTO {
  role: Role
  content: string
}

export interface ConversationResponse {
  conversation_id: string
  messages: ChatMessageDTO[]
}

// 会话列表项（GET /conversations）
export interface ConversationSummary {
  conversation_id: string
  title: string
  updated_at: number // Unix 时间戳（秒）
}

// SSE 流式回调
export interface ChatStreamHandlers {
  // 首个事件：服务端返回本轮会话 ID（新建会话时尤其重要）
  onConversationId?: (id: string) => void
  // 每个增量 token
  onToken?: (token: string) => void
  // 正常结束（收到 [DONE]）
  onDone?: () => void
  // 出错（网络错误或服务端 error 事件）
  onError?: (message: string) => void
}
