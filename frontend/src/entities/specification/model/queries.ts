import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/api';
import { getSpecification } from '../api/specificationApi';
import { specificationQueryKeys } from './types';

function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

export function useSpecification(projectId: string) {
  return useQuery({
    queryKey: specificationQueryKeys.detail(projectId),
    queryFn: () => getSpecification(projectId),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
    refetchInterval: (query) =>
      query.state.data?.generation?.status === 'queued' ||
      query.state.data?.generation?.status === 'running'
        ? 2000
        : false,
  });
}
