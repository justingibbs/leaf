// Project types
export interface Project {
  id: string
  path: string
  name: string
  created_at: string
  database_path?: string
}

export interface CreateProjectRequest {
  path: string
  name: string
}

export interface SwitchProjectRequest {
  project_id: string
}

// Card types
export interface TriggerConfig {
  type: 'file_created' | 'file_modified' | 'manual' | 'schedule'
  folder?: string
  pattern?: string
  cron?: string
}

export interface ProgramConfig {
  language: string
  entrypoint: string
  dependencies?: string[]
}

export interface Card {
  id: string
  name: string
  description?: string
  user_prompt?: string
  trigger_config: TriggerConfig
  program_config?: ProgramConfig
  program_path?: string
  timeout_seconds: number
  retry_count: number
  enabled: boolean
  created_at: string
  updated_at?: string
  run_count: number
  last_run_at?: string
}

export interface CreateCardRequest {
  name: string
  description?: string
  user_prompt?: string
  trigger_config: TriggerConfig
  program_config?: ProgramConfig
  timeout_seconds?: number
  retry_count?: number
  enabled?: boolean
}

export interface UpdateCardRequest {
  name?: string
  description?: string
  trigger_config?: TriggerConfig
  program_config?: ProgramConfig
  timeout_seconds?: number
  retry_count?: number
  enabled?: boolean
}

// Chat types
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface SendMessageRequest {
  content: string
}

export interface SendMessageResponse {
  response: string
  user_message_id: string
  assistant_message_id: string
}

// Execution types
export interface ExecutionResult {
  exit_code: number
  duration_seconds: number
  attempts: number
}

export interface Execution {
  id: string
  card_id: string
  event_id?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string
  completed_at?: string
  stdout?: string
  stderr?: string
  error?: string
  result?: ExecutionResult
}

// Event types
export interface FileEventPayload {
  path: string
  filename: string
  folder: string
  size?: number
}

export interface FileEvent {
  id: string
  type: 'file.created' | 'file.modified'
  timestamp: string
  payload: FileEventPayload
  status: 'pending' | 'processing' | 'completed' | 'failed'
  matched_cards?: string[]
  execution_id?: string
}

// MCP types
export interface McpServer {
  id: string
  name: string
  command: string
  args: string[]
  env: Record<string, string>
  enabled: boolean
  description?: string
  connected: boolean
}

export interface CreateMcpServerRequest {
  id: string
  name: string
  command: string
  args: string[]
  env?: Record<string, string>
  enabled?: boolean
  description?: string
}

export interface McpTool {
  server_id: string
  name: string
  description?: string
  parameters: Record<string, unknown>
}

export interface CallToolRequest {
  server_id: string
  tool_name: string
  arguments: Record<string, unknown>
}

export interface CallToolResponse {
  success: boolean
  output?: string
  error?: string
}

// WebSocket event types
export interface WsFileEvent {
  type: 'file.created' | 'file.modified'
  data: {
    event_id: string
    timestamp: string
    payload: FileEventPayload
    status: string
  }
}

export interface WsExecutionEvent {
  type: 'execution.started' | 'execution.completed' | 'execution.failed' | 'execution.retry'
  data: {
    execution_id: string
    card_id: string
    event_id?: string
    duration_seconds?: number
    error?: string
    attempt?: number
    max_attempts?: number
  }
}

export interface WsChatChunk {
  type: 'chunk'
  content: string
}

export interface WsChatDone {
  type: 'done'
}

export interface WsChatError {
  type: 'error'
  message: string
}

export type WsEvent = WsFileEvent | WsExecutionEvent
export type WsChatMessage = WsChatChunk | WsChatDone | WsChatError
