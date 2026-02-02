import { useEffect, useRef } from 'react'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ChatMessage, StreamingMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { useChatHistory, useClearChatHistory } from '@/hooks/useChatHistory'
import { useChatWebSocket } from '@/hooks/useChatWebSocket'

export function ChatPanel() {
  const { data: messages, isLoading } = useChatHistory()
  const clearHistory = useClearChatHistory()
  const { sendMessage, isStreaming, streamingContent, isConnected, error } = useChatWebSocket()
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, streamingContent])

  const handleClearHistory = async () => {
    await clearHistory.mutateAsync()
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b px-4 py-3 flex items-center justify-between bg-background">
        <div>
          <h2 className="font-semibold">Chat</h2>
          <p className="text-xs text-muted-foreground">
            {isConnected ? 'Connected' : 'Connecting...'}
          </p>
        </div>
        {messages && messages.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearHistory}
            disabled={clearHistory.isPending}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Clear
          </Button>
        )}
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1" ref={scrollRef}>
        <div className="divide-y">
          {isLoading ? (
            <div className="p-4 text-center text-muted-foreground">
              Loading chat history...
            </div>
          ) : messages && messages.length > 0 ? (
            <>
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isStreaming && streamingContent && (
                <StreamingMessage content={streamingContent} />
              )}
            </>
          ) : (
            <div className="p-8 text-center">
              <h3 className="font-medium mb-2">Welcome to LEAF</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                I can help you create automations. Try asking me to:
              </p>
              <ul className="text-sm text-muted-foreground mt-4 space-y-2">
                <li>"Create a card that processes CSV files in my inbox folder"</li>
                <li>"Watch for new images and resize them automatically"</li>
                <li>"Rename all PDFs in downloads with today's date"</li>
              </ul>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Error message */}
      {error && (
        <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        disabled={!isConnected || isStreaming}
        isStreaming={isStreaming}
      />
    </div>
  )
}
