import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Leaf, FolderOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { CreateProjectDialog } from '@/components/projects/CreateProjectDialog'
import { useProjects, useCreateProject, useSwitchProject, useDeleteProject } from '@/hooks/useProjects'
import { useAppStore, applyTheme } from '@/stores/appStore'

export function ProjectPicker() {
  const navigate = useNavigate()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const theme = useAppStore((s) => s.theme)

  const { data: projects, isLoading } = useProjects()
  const createProject = useCreateProject()
  const switchProject = useSwitchProject()
  const deleteProject = useDeleteProject()

  // Apply theme on mount
  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  const handleCreateProject = async (name: string, path: string) => {
    await createProject.mutateAsync({ name, path })
    navigate('/project')
  }

  const handleSelectProject = async (projectId: string) => {
    await switchProject.mutateAsync({ project_id: projectId })
    navigate('/project')
  }

  const handleDeleteProject = async (projectId: string) => {
    await deleteProject.mutateAsync(projectId)
  }

  const handleOpenExisting = async () => {
    try {
      const { open: openDialog } = await import('@tauri-apps/plugin-dialog')
      const selected = await openDialog({
        directory: true,
        title: 'Open Existing Project',
      })
      if (selected) {
        // Check if this path already exists
        const existing = projects?.find((p) => p.path === selected)
        if (existing) {
          await handleSelectProject(existing.id)
        } else {
          // Create a new project entry for this path
          const folderName = selected.split('/').pop() || selected.split('\\').pop() || 'Project'
          await createProject.mutateAsync({ name: folderName, path: selected })
          navigate('/project')
        }
      }
    } catch {
      console.log('Tauri dialog not available')
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Leaf className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">LEAF</h1>
            <p className="text-sm text-muted-foreground">Local Event-Driven Automation</p>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 p-6 max-w-4xl mx-auto w-full">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-medium">Your Projects</h2>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleOpenExisting}>
              <FolderOpen className="h-4 w-4 mr-2" />
              Open Existing
            </Button>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </div>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-muted-foreground">
            Loading projects...
          </div>
        ) : projects && projects.length > 0 ? (
          <ScrollArea className="h-[calc(100vh-200px)]">
            <div className="grid gap-3">
              {projects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onSelect={() => handleSelectProject(project.id)}
                  onDelete={() => handleDeleteProject(project.id)}
                />
              ))}
            </div>
          </ScrollArea>
        ) : (
          <div className="text-center py-12">
            <div className="p-4 bg-muted/50 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <Leaf className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="font-medium mb-1">No projects yet</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create a new project to start building automations
            </p>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Project
            </Button>
          </div>
        )}
      </main>

      <CreateProjectDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreate={handleCreateProject}
      />
    </div>
  )
}
