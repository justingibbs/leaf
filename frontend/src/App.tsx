import { Routes, Route, Navigate } from 'react-router-dom'
import { useProjectStore } from '@/stores/projectStore'
import { ProjectPicker } from '@/pages/ProjectPicker'
import { Dashboard } from '@/pages/Dashboard'
import { CardDetail } from '@/pages/CardDetail'
import { Executions } from '@/pages/Executions'
import { McpServers } from '@/pages/McpServers'
import { Settings } from '@/pages/Settings'
import { AppShell } from '@/components/layout/AppShell'

function RequireProject({ children }: { children: React.ReactNode }) {
  const currentProject = useProjectStore((state) => state.currentProject)

  if (!currentProject) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<ProjectPicker />} />
      <Route
        path="/project"
        element={
          <RequireProject>
            <AppShell />
          </RequireProject>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="cards/:cardId" element={<CardDetail />} />
        <Route path="executions" element={<Executions />} />
        <Route path="mcp" element={<McpServers />} />
      </Route>
      <Route path="/settings" element={<Settings />} />
    </Routes>
  )
}

export default App
