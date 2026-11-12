import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/api';
import { getProject, getProjectMembers, getProjectPassport, getProjects } from '../api/projectApi';
import { projectQueryKeys } from './types';

function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

export function useProjectList(archived: boolean, page: number) {
  return useQuery({
    queryKey: projectQueryKeys.list(archived ? 'archived' : 'ordinary', page),
    queryFn: () => getProjects(archived, page),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: projectQueryKeys.detail(projectId),
    queryFn: () => getProject(projectId),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}

export function useProjectMembers(projectId: string) {
  return useQuery({
    queryKey: projectQueryKeys.members(projectId),
    queryFn: () => getProjectMembers(projectId),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}

export function useProjectPassport(projectId: string) {
  return useQuery({
    queryKey: projectQueryKeys.passport(projectId),
    queryFn: () => getProjectPassport(projectId),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}
