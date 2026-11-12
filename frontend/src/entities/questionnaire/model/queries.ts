import { useQuery } from '@tanstack/react-query';
import { ApiError } from '../../../shared/api';
import { getProjectQuestionnaire, getProjectQuestionnaireConflicts } from '../api/questionnaireApi';
import { questionnaireQueryKeys } from './types';

function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

export function useProjectQuestionnaire(projectId: string) {
  return useQuery({
    queryKey: questionnaireQueryKeys.project(projectId),
    queryFn: () => getProjectQuestionnaire(projectId),
    enabled: Boolean(projectId),
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}

export function useProjectQuestionnaireConflicts(projectId: string, enabled: boolean) {
  return useQuery({
    queryKey: questionnaireQueryKeys.conflicts(projectId),
    queryFn: () => getProjectQuestionnaireConflicts(projectId),
    enabled: Boolean(projectId) && enabled,
    retry: shouldRetry,
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });
}
