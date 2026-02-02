import { Folder, Trash2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import type { Project } from '@/api/types'

interface ProjectCardProps {
  project: Project
  onSelect: () => void
  onDelete: () => void
}

export function ProjectCard({ project, onSelect, onDelete }: ProjectCardProps) {
  const createdDate = new Date(project.created_at).toLocaleDateString()

  return (
    <Card className="group cursor-pointer hover:border-primary/50 transition-colors">
      <CardContent className="p-4" onClick={onSelect}>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Folder className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium truncate">{project.name}</h3>
              <p className="text-sm text-muted-foreground truncate">{project.path}</p>
              <p className="text-xs text-muted-foreground mt-1">Created {createdDate}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
