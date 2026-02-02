import { ChatPanel } from '@/components/chat/ChatPanel'
import { EventQueue } from '@/components/events/EventQueue'

export function Dashboard() {
  return (
    <div className="h-full flex">
      {/* Main chat area */}
      <div className="flex-1">
        <ChatPanel />
      </div>

      {/* Event queue sidebar */}
      <div className="w-80 hidden lg:block">
        <EventQueue />
      </div>
    </div>
  )
}
