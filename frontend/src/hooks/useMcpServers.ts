import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { mcpApi } from '@/api'
import type { CreateMcpServerRequest } from '@/api/types'

export const mcpKeys = {
  servers: ['mcp', 'servers'] as const,
  server: (id: string) => ['mcp', 'servers', id] as const,
  tools: ['mcp', 'tools'] as const,
}

export function useMcpServers() {
  return useQuery({
    queryKey: mcpKeys.servers,
    queryFn: mcpApi.listMcpServers,
  })
}

export function useMcpServer(serverId: string) {
  return useQuery({
    queryKey: mcpKeys.server(serverId),
    queryFn: () => mcpApi.getMcpServer(serverId),
    enabled: !!serverId,
  })
}

export function useMcpTools() {
  return useQuery({
    queryKey: mcpKeys.tools,
    queryFn: mcpApi.listMcpTools,
  })
}

export function useAddMcpServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateMcpServerRequest) => mcpApi.addMcpServer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers })
    },
  })
}

export function useDeleteMcpServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (serverId: string) => mcpApi.deleteMcpServer(serverId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers })
    },
  })
}

export function useEnableMcpServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (serverId: string) => mcpApi.enableMcpServer(serverId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers })
    },
  })
}

export function useDisableMcpServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (serverId: string) => mcpApi.disableMcpServer(serverId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers })
    },
  })
}

export function useConnectMcpServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (serverId: string) => mcpApi.connectMcpServer(serverId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers })
      queryClient.invalidateQueries({ queryKey: mcpKeys.tools })
    },
  })
}

export function useDisconnectMcpServer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (serverId: string) => mcpApi.disconnectMcpServer(serverId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers })
      queryClient.invalidateQueries({ queryKey: mcpKeys.tools })
    },
  })
}

export function useConnectAllMcpServers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: mcpApi.connectAllMcpServers,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers })
      queryClient.invalidateQueries({ queryKey: mcpKeys.tools })
    },
  })
}

export function useDisconnectAllMcpServers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: mcpApi.disconnectAllMcpServers,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.servers })
      queryClient.invalidateQueries({ queryKey: mcpKeys.tools })
    },
  })
}
