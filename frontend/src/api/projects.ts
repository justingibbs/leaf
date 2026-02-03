import { get, post, del } from './client'
import type { Project, CreateProjectRequest, SwitchProjectRequest } from './types'

export async function listProjects(): Promise<Project[]> {
  return get<Project[]>('/api/projects')
}

export async function createProject(data: CreateProjectRequest): Promise<Project> {
  return post<Project>('/api/projects', data)
}

export async function getCurrentProject(): Promise<Project | null> {
  try {
    return await get<Project>('/api/projects/current')
  } catch {
    return null
  }
}

export async function switchProject(data: SwitchProjectRequest): Promise<Project> {
  return post<Project>('/api/projects/switch', data)
}

export async function closeProject(): Promise<{ status: string }> {
  return post('/api/projects/close')
}

export async function deleteProject(projectId: string): Promise<{ status: string }> {
  return del(`/api/projects/${projectId}`)
}
