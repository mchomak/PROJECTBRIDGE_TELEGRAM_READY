import { useQuery } from '@tanstack/react-query';
import { apiJson, ApiError } from '../../../shared/api';
import type { User } from './types';

export const currentUserQueryKey = ['currentUser'] as const;

export function useCurrentUser() {
  return useQuery<User, Error>({
    queryKey: currentUserQueryKey,
    queryFn: () => apiJson<User>('/api/v1/auth/me/'),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status < 500) return false;
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}
