import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { executionsApi } from '@/api'

export const executionKeys = {
  all: ['executions'] as const,
  list: (params?: { cardId?: string; status?: string }) =>
    params ? ['executions', params] : ['executions'],
  detail: (id: string) => ['executions', id] as const,
}

interface UseExecutionsParams {
  cardId?: string
  status?: 'pending' | 'running' | 'completed' | 'failed'
  limit?: number
}

export function useExecutions(params?: UseExecutionsParams) {
  return useQuery({
    queryKey: executionKeys.list(params),
    queryFn: () => executionsApi.listExecutions(params),
  })
}

export function useExecution(executionId: string) {
  return useQuery({
    queryKey: executionKeys.detail(executionId),
    queryFn: () => executionsApi.getExecution(executionId),
    enabled: !!executionId,
  })
}

export function useManualExecute() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (cardId: string) => executionsApi.manualExecute(cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: executionKeys.all })
    },
  })
}
