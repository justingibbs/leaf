import { useState } from 'react'
import { Server, Plus, Plug, Unplug } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { McpServerCard } from '@/components/mcp/McpServerCard'
import { AddServerDialog } from '@/components/mcp/AddServerDialog'
import {
  useMcpServers,
  useAddMcpServer,
  useDeleteMcpServer,
  useEnableMcpServer,
  useDisableMcpServer,
  useConnectMcpServer,
  useDisconnectMcpServer,
  useConnectAllMcpServers,
  useDisconnectAllMcpServers,
} from '@/hooks/useMcpServers'
import type { CreateMcpServerRequest } from '@/api/types'

export function McpServers() {
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const { data: servers, isLoading } = useMcpServers()
  const addServer = useAddMcpServer()
  const deleteServer = useDeleteMcpServer()
  const enableServer = useEnableMcpServer()
  const disableServer = useDisableMcpServer()
  const connectServer = useConnectMcpServer()
  const disconnectServer = useDisconnectMcpServer()
  const connectAll = useConnectAllMcpServers()
  const disconnectAll = useDisconnectAllMcpServers()

  const handleAddServer = async (data: CreateMcpServerRequest) => {
    await addServer.mutateAsync(data)
  }

  const connectedCount = servers?.filter((s) => s.connected).length || 0
  const enabledCount = servers?.filter((s) => s.enabled).length || 0

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Server className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">MCP Servers</h1>
              <p className="text-sm text-muted-foreground">
                {connectedCount} of {enabledCount} enabled servers connected
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {connectedCount > 0 ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => disconnectAll.mutate()}
                disabled={disconnectAll.isPending}
              >
                <Unplug className="h-4 w-4 mr-2" />
                Disconnect All
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => connectAll.mutate()}
                disabled={connectAll.isPending || enabledCount === 0}
              >
                <Plug className="h-4 w-4 mr-2" />
                Connect All
              </Button>
            )}
            <Button size="sm" onClick={() => setAddDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Server
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">
              Loading servers...
            </div>
          ) : servers && servers.length > 0 ? (
            servers.map((server) => (
              <McpServerCard
                key={server.id}
                server={server}
                onConnect={() => connectServer.mutate(server.id)}
                onDisconnect={() => disconnectServer.mutate(server.id)}
                onEnable={() => enableServer.mutate(server.id)}
                onDisable={() => disableServer.mutate(server.id)}
                onDelete={() => deleteServer.mutate(server.id)}
                isLoading={
                  connectServer.isPending ||
                  disconnectServer.isPending ||
                  enableServer.isPending ||
                  disableServer.isPending ||
                  deleteServer.isPending
                }
              />
            ))
          ) : (
            <div className="text-center py-8">
              <Server className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <h3 className="font-medium mb-1">No MCP servers configured</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Add MCP servers to extend LEAF's capabilities
              </p>
              <Button onClick={() => setAddDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Server
              </Button>
            </div>
          )}
        </div>
      </ScrollArea>

      <AddServerDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        onAdd={handleAddServer}
      />
    </div>
  )
}
