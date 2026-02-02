import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatApi } from '@/api'

export const chatKeys = {
  history: ['chat', 'history'] as const,
}

export function useChatHistory() {
  return useQuery({
    queryKey: chatKeys.history,
    queryFn: chatApi.getChatHistory,
  })
}

export function useClearChatHistory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: chatApi.clearChatHistory,
    onSuccess: () => {
      queryClient.setQueryData(chatKeys.history, [])
    },
  })
}
