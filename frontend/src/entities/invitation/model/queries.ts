import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/api';
import { getProjectInvitations } from '../api/invitationApi';
import { invitationQueryKeys } from './types';

function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

export function useProjectInvitations(projectId: string, page = 1) {
  return useQuery({
    queryKey: invitationQueryKeys.list(projectId, page),
    queryFn: () => getProjectInvitations(projectId, page),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}
