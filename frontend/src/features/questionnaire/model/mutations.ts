import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectQueryKeys } from '../../../entities/project';
import {
  requestQuestionnaireCorrection,
  refreshQuestionnaireDraftPassportVersion,
  resolveQuestionnaireConflict,
  saveQuestionnaireAnswers,
  startQuestionnaireSubmission,
  submitQuestionnaireSubmission,
  type ProjectQuestionnaire,
  type QuestionnaireAnswers,
  type QuestionnaireConflict,
  type QuestionnaireSubmission,
  type ResolveQuestionnaireConflictRequest,
  type SubmitQuestionnaireRequest,
  questionnaireQueryKeys,
} from '../../../entities/questionnaire';

function withLatestSubmission(
  current: ProjectQuestionnaire | undefined,
  submission: QuestionnaireSubmission,
): ProjectQuestionnaire | undefined {
  if (!current) return current;
  return {
    ...current,
    submission,
    history: [submission, ...current.history.filter((item) => item.id !== submission.id)],
  };
}

export function useStartQuestionnaireDraft(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<QuestionnaireSubmission, Error, void>({
    mutationFn: () => startQuestionnaireSubmission(projectId),
    onSuccess: (submission) => {
      queryClient.setQueryData<ProjectQuestionnaire>(
        questionnaireQueryKeys.project(projectId),
        (current) => withLatestSubmission(current, submission),
      );
    },
  });
}

export function useSaveQuestionnaireDraft(projectId: string, submissionId: string) {
  const queryClient = useQueryClient();
  return useMutation<QuestionnaireSubmission, Error, QuestionnaireAnswers>({
    mutationFn: (answers) => saveQuestionnaireAnswers(submissionId, answers),
    onSuccess: (submission) => {
      queryClient.setQueryData<ProjectQuestionnaire>(
        questionnaireQueryKeys.project(projectId),
        (current) => withLatestSubmission(current, submission),
      );
    },
  });
}

export function useSubmitQuestionnaire(projectId: string, submissionId: string) {
  const queryClient = useQueryClient();
  return useMutation<QuestionnaireSubmission, Error, SubmitQuestionnaireRequest>({
    mutationFn: (request) => submitQuestionnaireSubmission(submissionId, request),
    onSuccess: (submission) => {
      queryClient.setQueryData<ProjectQuestionnaire>(
        questionnaireQueryKeys.project(projectId),
        (current) => withLatestSubmission(current, submission),
      );
    },
  });
}

export function useRefreshQuestionnaireDraftPassportVersion(
  projectId: string,
  submissionId: string,
) {
  const queryClient = useQueryClient();
  return useMutation<QuestionnaireSubmission, Error, void>({
    mutationFn: () => refreshQuestionnaireDraftPassportVersion(submissionId),
    onSuccess: (submission) => {
      queryClient.setQueryData<ProjectQuestionnaire>(
        questionnaireQueryKeys.project(projectId),
        (current) => withLatestSubmission(current, submission),
      );
    },
  });
}

export function useRequestQuestionnaireCorrection(projectId: string, submissionId: string) {
  const queryClient = useQueryClient();
  return useMutation<QuestionnaireSubmission, Error, void>({
    mutationFn: () => requestQuestionnaireCorrection(submissionId),
    onSuccess: (correction) => {
      queryClient.setQueryData<ProjectQuestionnaire>(
        questionnaireQueryKeys.project(projectId),
        (current) => {
          if (!current) return current;
          const history = current.history.map((item) =>
            item.id === submissionId ? { ...item, status: 'correction_requested' as const } : item,
          );
          return {
            ...current,
            submission: correction,
            history: [correction, ...history.filter((item) => item.id !== correction.id)],
          };
        },
      );
    },
  });
}

export function useResolveQuestionnaireConflict(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    QuestionnaireConflict,
    Error,
    { conflictId: string; request: ResolveQuestionnaireConflictRequest }
  >({
    mutationFn: ({ conflictId, request }) => resolveQuestionnaireConflict(conflictId, request),
    onSuccess: (resolved) => {
      queryClient.setQueryData<QuestionnaireConflict[]>(
        questionnaireQueryKeys.conflicts(projectId),
        (current) => (current ?? []).filter((conflict) => conflict.id !== resolved.id),
      );
      void queryClient.invalidateQueries({ queryKey: projectQueryKeys.passport(projectId) });
    },
  });
}
