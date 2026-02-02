import { Server, Power, PowerOff, Plug, Unplug, Trash2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { McpServer } from '@/api/types'

interface McpServerCardProps {
  server: McpServer
  onConnect: () => void
  onDisconnect: () => void
  onEnable: () => void
  onDisable: () => void
  onDelete: () => void
  isLoading?: boolean
}

export function McpServerCard({
  server,
  onConnect,
  onDisconnect,
  onEnable,
  onDisable,
  onDelete,
  isLoading,
}: McpServerCardProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-muted rounded-lg">
              <Server className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium">{server.name}</h3>
                <Badge variant={server.enabled ? 'default' : 'secondary'}>
                  {server.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
                {server.connected && (
                  <Badge variant="outline" className="text-green-600 border-green-600">
                    Connected
                  </Badge>
                )}
              </div>
              {server.description && (
                <p className="text-sm text-muted-foreground mt-1">
                  {server.description}
                </p>
              )}
              <p className="text-xs text-muted-foreground mt-2 font-mono">
                {server.command} {server.args.join(' ')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {server.enabled && (
              server.connected ? (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onDisconnect}
                  disabled={isLoading}
                >
                  <Unplug className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onConnect}
                  disabled={isLoading}
                >
                  <Plug className="h-4 w-4" />
                </Button>
              )
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={server.enabled ? onDisable : onEnable}
              disabled={isLoading}
            >
              {server.enabled ? (
                <PowerOff className="h-4 w-4" />
              ) : (
                <Power className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onDelete}
              disabled={isLoading}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
