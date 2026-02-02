import { get, post } from './client'
import type { Execution } from './types'

interface ListExecutionsParams {
  cardId?: string
  status?: 'pending' | 'running' | 'completed' | 'failed'
  limit?: number
}

export async function listExecutions(params?: ListExecutionsParams): Promise<Execution[]> {
  const searchParams = new URLSearchParams()
  if (params?.cardId) searchParams.set('card_id', params.cardId)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.limit) searchParams.set('limit', params.limit.toString())

  const query = searchParams.toString()
  return get<Execution[]>(`/api/executions${query ? `?${query}` : ''}`)
}

export async function getExecution(executionId: string): Promise<Execution> {
  return get<Execution>(`/api/executions/${executionId}`)
}

export async function manualExecute(cardId: string): Promise<Execution> {
  return post<Execution>('/api/executions/manual', { card_id: cardId })
}
