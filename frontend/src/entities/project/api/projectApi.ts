import { apiJson } from '../../../shared/api';
import type { Project, ProjectMember, ProjectPage, ProjectPassport } from '../model/types';

export function getProjects(archived: boolean, page: number): Promise<ProjectPage> {
  const params = new URLSearchParams({ page: String(page) });
  if (archived) params.set('status', 'archived');
  return apiJson<ProjectPage>(`/api/v1/projects/?${params.toString()}`);
}

export function getProject(projectId: string): Promise<Project> {
  return apiJson<Project>(`/api/v1/projects/${encodeURIComponent(projectId)}/`);
}

export function getProjectMembers(projectId: string): Promise<ProjectMember[]> {
  return apiJson<ProjectMember[]>(`/api/v1/projects/${encodeURIComponent(projectId)}/members/`);
}

export function getProjectPassport(projectId: string): Promise<ProjectPassport> {
  return apiJson<ProjectPassport>(`/api/v1/projects/${encodeURIComponent(projectId)}/passport/`);
}
