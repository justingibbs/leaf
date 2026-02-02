import { get, post, patch, del } from './client'
import type { Card, CreateCardRequest, UpdateCardRequest } from './types'

export async function listCards(enabledOnly?: boolean): Promise<Card[]> {
  const query = enabledOnly ? '?enabled_only=true' : ''
  return get<Card[]>(`/api/cards${query}`)
}

export async function getCard(cardId: string): Promise<Card> {
  return get<Card>(`/api/cards/${cardId}`)
}

export async function createCard(data: CreateCardRequest): Promise<Card> {
  return post<Card>('/api/cards', data)
}

export async function updateCard(cardId: string, data: UpdateCardRequest): Promise<Card> {
  return patch<Card>(`/api/cards/${cardId}`, data)
}

export async function deleteCard(cardId: string): Promise<{ status: string }> {
  return del(`/api/cards/${cardId}`)
}

export async function enableCard(cardId: string): Promise<Card> {
  return post<Card>(`/api/cards/${cardId}/enable`)
}

export async function disableCard(cardId: string): Promise<Card> {
  return post<Card>(`/api/cards/${cardId}/disable`)
}

export async function triggerCard(cardId: string): Promise<{ status: string; execution_id: string }> {
  return post(`/api/cards/${cardId}/trigger`)
}

export async function getCardProgram(cardId: string): Promise<string> {
  const card = await getCard(cardId)
  if (!card.program_path) {
    return ''
  }
  // The program content would need a separate endpoint - for now return empty
  // TODO: Add endpoint to read program source
  return ''
}
