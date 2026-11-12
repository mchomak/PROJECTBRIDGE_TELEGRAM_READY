import { apiJson } from '../../../shared/api';
import type {
  ProjectQuestionnaire,
  QuestionnaireAnswers,
  QuestionnaireSubmission,
} from '../model/types';

export function getProjectQuestionnaire(projectId: string): Promise<ProjectQuestionnaire> {
  return apiJson<ProjectQuestionnaire>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/questionnaire/`,
  );
}

export function startQuestionnaireSubmission(projectId: string): Promise<QuestionnaireSubmission> {
  return apiJson<QuestionnaireSubmission>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/questionnaire/submissions/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    },
  );
}

export function saveQuestionnaireAnswers(
  submissionId: string,
  answers: QuestionnaireAnswers,
): Promise<QuestionnaireSubmission> {
  return apiJson<QuestionnaireSubmission>(
    `/api/v1/questionnaire/submissions/${encodeURIComponent(submissionId)}/answers/`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
    },
  );
}
