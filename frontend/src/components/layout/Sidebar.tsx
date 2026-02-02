import { NavLink, useLocation } from 'react-router-dom'
import { MessageSquare, History, Server, CreditCard } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { useCards } from '@/hooks/useCards'
import { useAppStore } from '@/stores/appStore'

const navItems = [
  { to: '/project', icon: MessageSquare, label: 'Chat', exact: true },
  { to: '/project/executions', icon: History, label: 'Executions' },
  { to: '/project/mcp', icon: Server, label: 'MCP Servers' },
]

export function Sidebar() {
  const location = useLocation()
  const { sidebarCollapsed } = useAppStore()
  const { data: cards } = useCards()

  return (
    <aside
      className={cn(
        'border-r bg-sidebar-background flex flex-col transition-all duration-200',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Navigation */}
      <nav className="p-2 space-y-1">
        {navItems.map(({ to, icon: Icon, label, exact }) => {
          const isActive = exact
            ? location.pathname === to
            : location.pathname.startsWith(to)

          return (
            <NavLink
              key={to}
              to={to}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!sidebarCollapsed && <span>{label}</span>}
            </NavLink>
          )
        })}
      </nav>

      <Separator className="my-2" />

      {/* Cards section */}
      {!sidebarCollapsed && (
        <>
          <div className="px-4 py-2 flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">Cards</span>
            <Badge variant="secondary" className="text-xs">
              {cards?.length || 0}
            </Badge>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {cards?.map((card) => {
                const isActive = location.pathname === `/project/cards/${card.id}`
                return (
                  <NavLink
                    key={card.id}
                    to={`/project/cards/${card.id}`}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                      isActive
                        ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                        : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                    )}
                  >
                    <CreditCard className="h-4 w-4 shrink-0" />
                    <span className="truncate flex-1">{card.name}</span>
                    {!card.enabled && (
                      <Badge variant="outline" className="text-xs">
                        Off
                      </Badge>
                    )}
                  </NavLink>
                )
              })}
              {(!cards || cards.length === 0) && (
                <p className="text-xs text-muted-foreground px-3 py-2">
                  No cards yet. Use the chat to create one.
                </p>
              )}
            </div>
          </ScrollArea>
        </>
      )}

      {sidebarCollapsed && (
        <div className="flex-1 p-2">
          <Button variant="ghost" size="icon" className="w-full" asChild>
            <NavLink to="/project">
              <CreditCard className="h-4 w-4" />
            </NavLink>
          </Button>
        </div>
      )}
    </aside>
  )
}
