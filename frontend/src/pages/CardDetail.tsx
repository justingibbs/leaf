import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Play,
  Trash2,
  Power,
  PowerOff,
  FolderOpen,
  FileCode,
  Clock,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CardEditor } from '@/components/cards/CardEditor'
import { CardExecutions } from '@/components/cards/CardExecutions'
import {
  useCard,
  useDeleteCard,
  useEnableCard,
  useDisableCard,
  useTriggerCard,
} from '@/hooks/useCards'

export function CardDetail() {
  const { cardId } = useParams<{ cardId: string }>()
  const navigate = useNavigate()
  const { data: card, isLoading } = useCard(cardId!)
  const deleteCard = useDeleteCard()
  const enableCard = useEnableCard()
  const disableCard = useDisableCard()
  const triggerCard = useTriggerCard()

  if (isLoading) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        Loading card...
      </div>
    )
  }

  if (!card) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground mb-4">Card not found</p>
        <Button variant="outline" onClick={() => navigate('/project')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>
      </div>
    )
  }

  const handleToggleEnabled = async () => {
    if (card.enabled) {
      await disableCard.mutateAsync(card.id)
    } else {
      await enableCard.mutateAsync(card.id)
    }
  }

  const handleTrigger = async () => {
    await triggerCard.mutateAsync(card.id)
  }

  const handleDelete = async () => {
    await deleteCard.mutateAsync(card.id)
    navigate('/project')
  }

  const triggerTypeLabels: Record<string, string> = {
    file_created: 'File Created',
    file_modified: 'File Modified',
    manual: 'Manual',
    schedule: 'Schedule',
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate('/project')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-xl font-semibold">{card.name}</h1>
              {card.description && (
                <p className="text-sm text-muted-foreground">{card.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleEnabled}
              disabled={enableCard.isPending || disableCard.isPending}
            >
              {card.enabled ? (
                <>
                  <PowerOff className="h-4 w-4 mr-2" />
                  Disable
                </>
              ) : (
                <>
                  <Power className="h-4 w-4 mr-2" />
                  Enable
                </>
              )}
            </Button>
            <Button
              size="sm"
              onClick={handleTrigger}
              disabled={triggerCard.isPending}
            >
              <Play className="h-4 w-4 mr-2" />
              Run Now
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleteCard.isPending}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>

        {/* Card info */}
        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Badge variant={card.enabled ? 'default' : 'secondary'}>
              {card.enabled ? 'Enabled' : 'Disabled'}
            </Badge>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <FileCode className="h-4 w-4" />
            <span>
              {triggerTypeLabels[card.trigger_config.type] || card.trigger_config.type}
            </span>
          </div>
          {card.trigger_config.folder && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <FolderOpen className="h-4 w-4" />
              <span>{card.trigger_config.folder}</span>
              {card.trigger_config.pattern && (
                <Badge variant="outline">{card.trigger_config.pattern}</Badge>
              )}
            </div>
          )}
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>{card.timeout_seconds}s timeout</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <RefreshCw className="h-4 w-4" />
            <span>{card.retry_count} retries</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="code" className="h-full flex flex-col">
          <div className="border-b px-4">
            <TabsList>
              <TabsTrigger value="code">Code</TabsTrigger>
              <TabsTrigger value="executions">
                Executions ({card.run_count})
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="code" className="flex-1 m-0">
            <CardEditor
              initialCode="# Program code would be loaded here\n# (Requires backend endpoint to read program source)"
              readOnly
            />
          </TabsContent>
          <TabsContent value="executions" className="flex-1 m-0 overflow-hidden">
            <CardExecutions cardId={card.id} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
