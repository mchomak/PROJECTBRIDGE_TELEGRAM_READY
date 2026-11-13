import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/api';
import { getAIAnalysisRequests, getAIProposals } from '../api/aiAnalysisApi';
import { aiAnalysisQueryKeys } from './types';

function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

export function useAIAnalysisRequests(projectId: string, enabled: boolean) {
  return useQuery({
    queryKey: aiAnalysisQueryKeys.requests(projectId),
    queryFn: () => getAIAnalysisRequests(projectId),
    enabled: Boolean(projectId) && enabled,
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
    refetchInterval: (query) =>
      query.state.data?.some(
        (request) => request.status === 'queued' || request.status === 'running',
      )
        ? 2500
        : false,
  });
}

export function useAIProposals(projectId: string, enabled: boolean) {
  return useQuery({
    queryKey: aiAnalysisQueryKeys.proposals(projectId),
    queryFn: () => getAIProposals(projectId),
    enabled: Boolean(projectId) && enabled,
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}
