import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/api';
import {
  getProjectStateAggregate,
  getProjectStateCollection,
  getProjectStateEvidenceOptions,
} from '../api/projectStateApi';
import { projectStateQueryKeys } from './types';
import type { ProjectStateCollection } from './types';

function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

export function useProjectStateAggregate(projectId: string) {
  return useQuery({
    queryKey: projectStateQueryKeys.aggregate(projectId),
    queryFn: () => getProjectStateAggregate(projectId),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}

export function useProjectStateCollection<K extends ProjectStateCollection>(
  projectId: string,
  collection: K,
) {
  return useQuery({
    queryKey: projectStateQueryKeys.collection(projectId, collection),
    queryFn: () => getProjectStateCollection(projectId, collection),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}

export function useProjectStateEvidenceOptions(projectId: string, enabled: boolean) {
  return useQuery({
    queryKey: projectStateQueryKeys.evidenceOptions(projectId),
    queryFn: () => getProjectStateEvidenceOptions(projectId),
    enabled: Boolean(projectId) && enabled,
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}
