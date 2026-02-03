import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi } from '@/api'
import type { CreateProjectRequest, SwitchProjectRequest } from '@/api/types'
import { useProjectStore } from '@/stores/projectStore'

export const projectKeys = {
  all: ['projects'] as const,
  current: ['projects', 'current'] as const,
}

export function useProjects() {
  return useQuery({
    queryKey: projectKeys.all,
    queryFn: projectsApi.listProjects,
  })
}

export function useCurrentProject() {
  return useQuery({
    queryKey: projectKeys.current,
    queryFn: projectsApi.getCurrentProject,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)

  return useMutation({
    mutationFn: (data: CreateProjectRequest) => projectsApi.createProject(data),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all })
      setCurrentProject(project)
    },
  })
}

export function useSwitchProject() {
  const queryClient = useQueryClient()
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)

  return useMutation({
    mutationFn: (data: SwitchProjectRequest) => projectsApi.switchProject(data),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.current })
      setCurrentProject(project)
    },
  })
}

export function useCloseProject() {
  const queryClient = useQueryClient()
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject)

  return useMutation({
    mutationFn: projectsApi.closeProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.current })
      setCurrentProject(null)
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectId: string) => projectsApi.deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all })
    },
  })
}
