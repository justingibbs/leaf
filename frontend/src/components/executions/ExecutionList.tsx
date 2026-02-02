import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle, XCircle, Loader2, Clock, ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { Execution } from '@/api/types'

interface ExecutionListProps {
  executions: Execution[]
  showCard?: boolean
}

const statusConfig = {
  pending: { icon: Clock, color: 'text-muted-foreground', bg: 'bg-muted' },
  running: { icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
}

function ExecutionRow({ execution, showCard }: { execution: Execution; showCard?: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const config = statusConfig[execution.status]
  const StatusIcon = config.icon
  const startTime = new Date(execution.started_at).toLocaleString()

  return (
    <div className="border-b">
      <div
        className={cn(
          'flex items-center gap-4 p-4 hover:bg-muted/50 cursor-pointer',
          config.bg
        )}
        onClick={() => setExpanded(!expanded)}
      >
        <Button variant="ghost" size="icon" className="h-6 w-6">
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </Button>
        <StatusIcon
          className={cn(
            'h-5 w-5',
            config.color,
            execution.status === 'running' && 'animate-spin'
          )}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm truncate">{execution.id}</span>
            {showCard && (
              <Link
                to={`/project/cards/${execution.card_id}`}
                className="text-sm text-primary hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                View Card
              </Link>
            )}
          </div>
          <p className="text-sm text-muted-foreground">{startTime}</p>
        </div>
        <div className="text-right">
          <Badge variant="outline">{execution.status}</Badge>
          {execution.result && (
            <p className="text-xs text-muted-foreground mt-1">
              {execution.result.duration_seconds.toFixed(2)}s
            </p>
          )}
        </div>
      </div>
      {expanded && (
        <div className="px-14 pb-4 space-y-3">
          {execution.error && (
            <div className="p-3 bg-destructive/10 rounded-md">
              <p className="text-sm font-medium text-destructive">Error</p>
              <pre className="text-sm text-destructive/80 mt-1 whitespace-pre-wrap">
                {execution.error}
              </pre>
            </div>
          )}
          {execution.stdout && (
            <div className="p-3 bg-muted rounded-md">
              <p className="text-sm font-medium mb-1">Output</p>
              <pre className="text-sm text-muted-foreground whitespace-pre-wrap font-mono">
                {execution.stdout}
              </pre>
            </div>
          )}
          {execution.stderr && (
            <div className="p-3 bg-orange-500/10 rounded-md">
              <p className="text-sm font-medium text-orange-600">Stderr</p>
              <pre className="text-sm text-orange-600/80 mt-1 whitespace-pre-wrap font-mono">
                {execution.stderr}
              </pre>
            </div>
          )}
          {execution.result && (
            <div className="text-sm text-muted-foreground">
              Exit code: {execution.result.exit_code} |
              Duration: {execution.result.duration_seconds.toFixed(2)}s |
              Attempts: {execution.result.attempts}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ExecutionList({ executions, showCard = true }: ExecutionListProps) {
  if (executions.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <p className="text-sm">No executions found</p>
      </div>
    )
  }

  return (
    <div className="divide-y">
      {executions.map((execution) => (
        <ExecutionRow key={execution.id} execution={execution} showCard={showCard} />
      ))}
    </div>
  )
}
