import { File, FileEdit, CheckCircle, XCircle, Loader2, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import type { FileEvent } from '@/api/types'

interface EventItemProps {
  event: FileEvent
}

const statusIcons = {
  pending: Clock,
  processing: Loader2,
  completed: CheckCircle,
  failed: XCircle,
}

const statusColors = {
  pending: 'text-muted-foreground',
  processing: 'text-blue-500',
  completed: 'text-green-500',
  failed: 'text-red-500',
}

export function EventItem({ event }: EventItemProps) {
  const StatusIcon = statusIcons[event.status]
  const eventTime = new Date(event.timestamp).toLocaleTimeString()

  return (
    <div className="flex items-start gap-3 p-3 hover:bg-muted/50 transition-colors">
      <div className="p-1.5 bg-muted rounded-md">
        {event.type === 'file.created' ? (
          <File className="h-4 w-4 text-muted-foreground" />
        ) : (
          <FileEdit className="h-4 w-4 text-muted-foreground" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">
            {event.payload.filename}
          </span>
          <Badge variant="outline" className="text-xs shrink-0">
            {event.type === 'file.created' ? 'Created' : 'Modified'}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground truncate">
          {event.payload.folder}
        </p>
        {event.matched_cards && event.matched_cards.length > 0 && (
          <p className="text-xs text-muted-foreground mt-1">
            Matched {event.matched_cards.length} card(s)
          </p>
        )}
      </div>
      <div className="flex flex-col items-end gap-1">
        <StatusIcon
          className={cn(
            'h-4 w-4',
            statusColors[event.status],
            event.status === 'processing' && 'animate-spin'
          )}
        />
        <span className="text-xs text-muted-foreground">{eventTime}</span>
      </div>
    </div>
  )
}
