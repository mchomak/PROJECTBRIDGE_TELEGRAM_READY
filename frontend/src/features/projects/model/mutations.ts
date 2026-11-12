import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { components } from '../../../shared/api/generated/schema';
import { apiJson } from '../../../shared/api';
import { projectQueryKeys, type Project, type ProjectPassport } from '../../../entities/project';

type ProjectCreate = components['schemas']['ProjectCreate'];
type ProjectMetadataUpdate = components['schemas']['PatchedProjectMetadataUpdate'];
export type PassportUpdate = components['schemas']['ProjectPassportPatchSchema'];
export type LifecycleAction = 'complete' | 'reopen' | 'archive' | 'restore';

function projectPath(projectId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/`;
}

function postProjectJson<T>(path: string, body?: unknown): Promise<T> {
  return apiJson<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation<Project, Error, ProjectCreate>({
    mutationFn: (data) => postProjectJson<Project>('/api/v1/projects/', data),
    onSuccess: async (project) => {
      queryClient.setQueryData(projectQueryKeys.detail(project.id), project);
      await queryClient.invalidateQueries({ queryKey: projectQueryKeys.lists() });
    },
  });
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<Project, Error, ProjectMetadataUpdate>({
    mutationFn: (changes) =>
      apiJson<Project>(projectPath(projectId), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(changes),
      }),
    onSuccess: async (project) => {
      queryClient.setQueryData(projectQueryKeys.detail(projectId), project);
      await queryClient.invalidateQueries({ queryKey: projectQueryKeys.lists() });
    },
  });
}

export function useProjectLifecycleAction(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<Project, Error, LifecycleAction>({
    mutationFn: (action) => postProjectJson<Project>(`${projectPath(projectId)}${action}/`),
    onSuccess: async (project) => {
      queryClient.setQueryData(projectQueryKeys.detail(projectId), project);
      await queryClient.invalidateQueries({ queryKey: projectQueryKeys.lists() });
    },
  });
}

export function useUpdatePassport(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<ProjectPassport, Error, PassportUpdate>({
    mutationFn: (changes) =>
      apiJson<ProjectPassport>(`${projectPath(projectId)}passport/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(changes),
      }),
    onSuccess: (passport) => {
      queryClient.setQueryData(projectQueryKeys.passport(projectId), passport);
    },
  });
}
