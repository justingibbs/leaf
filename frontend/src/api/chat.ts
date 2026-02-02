import { get, post, del } from './client'
import type { ChatMessage, SendMessageRequest, SendMessageResponse } from './types'

export async function getChatHistory(): Promise<ChatMessage[]> {
  return get<ChatMessage[]>('/api/chat/history')
}

export async function sendMessage(data: SendMessageRequest): Promise<SendMessageResponse> {
  return post<SendMessageResponse>('/api/chat', data)
}

export async function clearChatHistory(): Promise<{ status: string }> {
  return del('/api/chat/history')
}
