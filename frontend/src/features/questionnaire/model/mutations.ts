import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  saveQuestionnaireAnswers,
  startQuestionnaireSubmission,
  type ProjectQuestionnaire,
  type QuestionnaireAnswers,
  type QuestionnaireSubmission,
  questionnaireQueryKeys,
} from '../../../entities/questionnaire';

export function useStartQuestionnaireDraft(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<QuestionnaireSubmission, Error, void>({
    mutationFn: () => startQuestionnaireSubmission(projectId),
    onSuccess: (submission) => {
      queryClient.setQueryData<ProjectQuestionnaire>(
        questionnaireQueryKeys.project(projectId),
        (current) => (current ? { ...current, submission } : current),
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
        (current) => (current ? { ...current, submission } : current),
      );
    },
  });
}
