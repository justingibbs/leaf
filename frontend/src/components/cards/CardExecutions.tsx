import { CheckCircle, XCircle, Loader2, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useExecutions } from '@/hooks/useExecutions'
import type { Execution } from '@/api/types'

interface CardExecutionsProps {
  cardId: string
}

const statusConfig = {
  pending: { icon: Clock, color: 'text-muted-foreground', label: 'Pending' },
  running: { icon: Loader2, color: 'text-blue-500', label: 'Running' },
  completed: { icon: CheckCircle, color: 'text-green-500', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-500', label: 'Failed' },
}

function ExecutionItem({ execution }: { execution: Execution }) {
  const config = statusConfig[execution.status]
  const StatusIcon = config.icon
  const startTime = new Date(execution.started_at).toLocaleString()

  return (
    <div className="p-3 border-b hover:bg-muted/50">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <StatusIcon
            className={cn(
              'h-4 w-4',
              config.color,
              execution.status === 'running' && 'animate-spin'
            )}
          />
          <Badge variant="outline" className="text-xs">
            {config.label}
          </Badge>
        </div>
        <span className="text-xs text-muted-foreground">{startTime}</span>
      </div>
      {execution.result && (
        <div className="text-xs text-muted-foreground mt-1">
          Duration: {execution.result.duration_seconds.toFixed(2)}s
          {execution.result.attempts > 1 && ` (${execution.result.attempts} attempts)`}
        </div>
      )}
      {execution.error && (
        <div className="text-xs text-destructive mt-1 truncate">
          {execution.error}
        </div>
      )}
    </div>
  )
}

export function CardExecutions({ cardId }: CardExecutionsProps) {
  const { data: executions, isLoading } = useExecutions({ cardId, limit: 20 })

  if (isLoading) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        Loading executions...
      </div>
    )
  }

  if (!executions || executions.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <p className="text-sm">No executions yet</p>
        <p className="text-xs mt-1">
          Trigger this card to see execution history
        </p>
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      {executions.map((execution) => (
        <ExecutionItem key={execution.id} execution={execution} />
      ))}
    </ScrollArea>
  )
}
