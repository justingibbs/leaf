import { Trash2, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EventItem } from './EventItem'
import { useEventStore } from '@/stores/eventStore'

export function EventQueue() {
  const { events, clearEvents } = useEventStore()

  return (
    <div className="h-full flex flex-col border-l bg-background">
      {/* Header */}
      <div className="border-b px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-medium">Events</h3>
        </div>
        {events.length > 0 && (
          <Button variant="ghost" size="sm" onClick={clearEvents}>
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Events list */}
      <ScrollArea className="flex-1">
        {events.length > 0 ? (
          <div className="divide-y">
            {events.map((event) => (
              <EventItem key={event.id} event={event} />
            ))}
          </div>
        ) : (
          <div className="p-4 text-center text-muted-foreground">
            <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No recent events</p>
            <p className="text-xs mt-1">
              Events will appear here when files are added to watched folders
            </p>
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
