import { useState } from 'react'
import { History, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ExecutionList } from '@/components/executions/ExecutionList'
import { useExecutions } from '@/hooks/useExecutions'

type StatusFilter = 'all' | 'pending' | 'running' | 'completed' | 'failed'

export function Executions() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const { data: executions, isLoading, refetch, isRefetching } = useExecutions({
    status: statusFilter === 'all' ? undefined : statusFilter,
    limit: 100,
  })

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <History className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">Executions</h1>
              <p className="text-sm text-muted-foreground">
                View execution history for all cards
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isRefetching}
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', isRefetching && 'animate-spin')} />
            Refresh
          </Button>
        </div>

        <Tabs value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="running">Running</TabsTrigger>
            <TabsTrigger value="completed">Completed</TabsTrigger>
            <TabsTrigger value="failed">Failed</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">
            Loading executions...
          </div>
        ) : executions ? (
          <ExecutionList executions={executions} />
        ) : (
          <div className="p-8 text-center text-muted-foreground">
            Failed to load executions
          </div>
        )}
      </ScrollArea>
    </div>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}
