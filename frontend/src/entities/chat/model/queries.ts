import { useInfiniteQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/api';
import { getProjectMessages, getProjectMessageCursor } from '../api/chatApi';
import { chatQueryKeys } from './types';

function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

export function useProjectMessages(projectId: string) {
  return useInfiniteQuery({
    queryKey: chatQueryKeys.history(projectId),
    queryFn: ({ pageParam }) => getProjectMessages(projectId, pageParam ?? undefined),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => getProjectMessageCursor(page.next),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}
