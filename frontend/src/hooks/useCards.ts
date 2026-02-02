import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cardsApi } from '@/api'
import type { CreateCardRequest, UpdateCardRequest } from '@/api/types'

export const cardKeys = {
  all: ['cards'] as const,
  detail: (id: string) => ['cards', id] as const,
}

export function useCards(enabledOnly?: boolean) {
  return useQuery({
    queryKey: cardKeys.all,
    queryFn: () => cardsApi.listCards(enabledOnly),
  })
}

export function useCard(cardId: string) {
  return useQuery({
    queryKey: cardKeys.detail(cardId),
    queryFn: () => cardsApi.getCard(cardId),
    enabled: !!cardId,
  })
}

export function useCreateCard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateCardRequest) => cardsApi.createCard(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cardKeys.all })
    },
  })
}

export function useUpdateCard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ cardId, data }: { cardId: string; data: UpdateCardRequest }) =>
      cardsApi.updateCard(cardId, data),
    onSuccess: (card) => {
      queryClient.invalidateQueries({ queryKey: cardKeys.all })
      queryClient.setQueryData(cardKeys.detail(card.id), card)
    },
  })
}

export function useDeleteCard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cardId: string) => cardsApi.deleteCard(cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cardKeys.all })
    },
  })
}

export function useEnableCard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cardId: string) => cardsApi.enableCard(cardId),
    onSuccess: (card) => {
      queryClient.invalidateQueries({ queryKey: cardKeys.all })
      queryClient.setQueryData(cardKeys.detail(card.id), card)
    },
  })
}

export function useDisableCard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cardId: string) => cardsApi.disableCard(cardId),
    onSuccess: (card) => {
      queryClient.invalidateQueries({ queryKey: cardKeys.all })
      queryClient.setQueryData(cardKeys.detail(card.id), card)
    },
  })
}

export function useTriggerCard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cardId: string) => cardsApi.triggerCard(cardId),
    onSuccess: () => {
      // Invalidate executions since a new one was created
      queryClient.invalidateQueries({ queryKey: ['executions'] })
    },
  })
}
