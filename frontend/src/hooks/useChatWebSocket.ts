import { useState, useCallback, useRef, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getWebSocketUrl } from '@/api/client'
import type { WsChatMessage, ChatMessage } from '@/api/types'
import { chatKeys } from './useChatHistory'

interface UseChatWebSocketReturn {
  sendMessage: (content: string) => void
  isConnected: boolean
  isStreaming: boolean
  streamingContent: string
  error: string | null
}

export function useChatWebSocket(): UseChatWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const queryClient = useQueryClient()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const ws = new WebSocket(getWebSocketUrl('/ws/chat'))

    ws.onopen = () => {
      setIsConnected(true)
      setError(null)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WsChatMessage

        if (data.type === 'chunk') {
          setStreamingContent((prev) => prev + data.content)
        } else if (data.type === 'done') {
          setIsStreaming(false)
          // Invalidate chat history to refetch with complete messages
          queryClient.invalidateQueries({ queryKey: chatKeys.history })
          setStreamingContent('')
        } else if (data.type === 'error') {
          setError(data.message)
          setIsStreaming(false)
          setStreamingContent('')
        }
      } catch (err) {
        console.error('Failed to parse chat message:', err)
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
    }

    ws.onerror = () => {
      setError('Connection error')
      setIsConnected(false)
    }

    wsRef.current = ws
  }, [queryClient])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected')
      return
    }

    // Add user message to cache immediately for optimistic update
    queryClient.setQueryData<ChatMessage[]>(chatKeys.history, (old) => {
      const userMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      }
      return [...(old || []), userMessage]
    })

    setIsStreaming(true)
    setStreamingContent('')
    setError(null)

    wsRef.current.send(JSON.stringify({
      type: 'message',
      content,
    }))
  }, [queryClient])

  useEffect(() => {
    connect()
    return disconnect
  }, [connect, disconnect])

  return {
    sendMessage,
    isConnected,
    isStreaming,
    streamingContent,
    error,
  }
}
