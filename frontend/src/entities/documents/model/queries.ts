import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/api';
import { getProjectDocuments } from '../api/documentsApi';
import { documentQueryKeys } from './types';

function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

export function useProjectDocuments(projectId: string, page: number) {
  return useQuery({
    queryKey: documentQueryKeys.page(projectId, page),
    queryFn: () => getProjectDocuments(projectId, page),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}
