import { Link, useNavigate } from 'react-router-dom'
import { Leaf, Settings, Moon, Sun, FolderOpen, PanelLeftClose, PanelLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useProjectStore } from '@/stores/projectStore'
import { useAppStore, applyTheme } from '@/stores/appStore'
import { useCloseProject } from '@/hooks/useProjects'

export function Header() {
  const navigate = useNavigate()
  const currentProject = useProjectStore((s) => s.currentProject)
  const { theme, setTheme, sidebarCollapsed, toggleSidebar } = useAppStore()
  const closeProject = useCloseProject()

  const handleThemeToggle = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    applyTheme(newTheme)
  }

  const handleCloseProject = async () => {
    await closeProject.mutateAsync()
    navigate('/')
  }

  return (
    <header className="h-14 border-b px-4 flex items-center justify-between bg-background">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={toggleSidebar}>
          {sidebarCollapsed ? (
            <PanelLeft className="h-5 w-5" />
          ) : (
            <PanelLeftClose className="h-5 w-5" />
          )}
        </Button>
        <Link to="/project" className="flex items-center gap-2">
          <div className="p-1.5 bg-primary/10 rounded-md">
            <Leaf className="h-4 w-4 text-primary" />
          </div>
          <span className="font-semibold">LEAF</span>
        </Link>
        {currentProject && (
          <>
            <span className="text-muted-foreground">/</span>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="gap-2">
                  <FolderOpen className="h-4 w-4" />
                  {currentProject.name}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem disabled>
                  <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                    {currentProject.path}
                  </span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleCloseProject}>
                  Close Project
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={handleThemeToggle}>
          {theme === 'dark' ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </Button>
        <Button variant="ghost" size="icon" asChild>
          <Link to="/settings">
            <Settings className="h-5 w-5" />
          </Link>
        </Button>
      </div>
    </header>
  )
}
