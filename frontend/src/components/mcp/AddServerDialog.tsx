import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { CreateMcpServerRequest } from '@/api/types'

interface AddServerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (data: CreateMcpServerRequest) => void
}

export function AddServerDialog({ open, onOpenChange, onAdd }: AddServerDialogProps) {
  const [id, setId] = useState('')
  const [name, setName] = useState('')
  const [command, setCommand] = useState('')
  const [args, setArgs] = useState('')
  const [description, setDescription] = useState('')

  const handleAdd = () => {
    if (id && name && command) {
      onAdd({
        id,
        name,
        command,
        args: args.split(' ').filter(Boolean),
        description: description || undefined,
        enabled: true,
      })
      // Reset form
      setId('')
      setName('')
      setCommand('')
      setArgs('')
      setDescription('')
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add MCP Server</DialogTitle>
          <DialogDescription>
            Configure a new MCP server to extend LEAF's capabilities.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">ID</label>
              <Input
                placeholder="my-server"
                value={id}
                onChange={(e) => setId(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Name</label>
              <Input
                placeholder="My Custom Server"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Command</label>
            <Input
              placeholder="npx"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Arguments (space-separated)</label>
            <Input
              placeholder="-y @anthropic/mcp-server-fetch"
              value={args}
              onChange={(e) => setArgs(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea
              placeholder="What does this server do?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleAdd} disabled={!id || !name || !command}>
            Add Server
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
