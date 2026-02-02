import { get, post, del } from './client'
import type { McpServer, CreateMcpServerRequest, McpTool, CallToolRequest, CallToolResponse } from './types'

export async function listMcpServers(): Promise<McpServer[]> {
  return get<McpServer[]>('/api/mcp/servers')
}

export async function getMcpServer(serverId: string): Promise<McpServer> {
  return get<McpServer>(`/api/mcp/servers/${serverId}`)
}

export async function addMcpServer(data: CreateMcpServerRequest): Promise<McpServer> {
  return post<McpServer>('/api/mcp/servers', data)
}

export async function deleteMcpServer(serverId: string): Promise<{ status: string }> {
  return del(`/api/mcp/servers/${serverId}`)
}

export async function enableMcpServer(serverId: string): Promise<McpServer> {
  return post<McpServer>(`/api/mcp/servers/${serverId}/enable`)
}

export async function disableMcpServer(serverId: string): Promise<McpServer> {
  return post<McpServer>(`/api/mcp/servers/${serverId}/disable`)
}

export async function connectMcpServer(serverId: string): Promise<McpServer> {
  return post<McpServer>(`/api/mcp/servers/${serverId}/connect`)
}

export async function disconnectMcpServer(serverId: string): Promise<McpServer> {
  return post<McpServer>(`/api/mcp/servers/${serverId}/disconnect`)
}

export async function listMcpTools(): Promise<McpTool[]> {
  return get<McpTool[]>('/api/mcp/tools')
}

export async function callMcpTool(data: CallToolRequest): Promise<CallToolResponse> {
  return post<CallToolResponse>('/api/mcp/tools/call', data)
}

export async function connectAllMcpServers(): Promise<{ connected: string[] }> {
  return post('/api/mcp/connect-all')
}

export async function disconnectAllMcpServers(): Promise<{ status: string }> {
  return post('/api/mcp/disconnect-all')
}
