import { apiJson } from '../../../shared/api';
import type {
  ProjectQuestionnaire,
  QuestionnaireAnswers,
  QuestionnaireConflict,
  QuestionnaireSubmission,
  ResolveQuestionnaireConflictRequest,
  SubmitQuestionnaireRequest,
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

export function refreshQuestionnaireDraftPassportVersion(
  submissionId: string,
): Promise<QuestionnaireSubmission> {
  return apiJson<QuestionnaireSubmission>(
    `/api/v1/questionnaire/submissions/${encodeURIComponent(submissionId)}/refresh-passport-version/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    },
  );
}

export function submitQuestionnaireSubmission(
  submissionId: string,
  request: SubmitQuestionnaireRequest,
): Promise<QuestionnaireSubmission> {
  return apiJson<QuestionnaireSubmission>(
    `/api/v1/questionnaire/submissions/${encodeURIComponent(submissionId)}/submit/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    },
  );
}

export function requestQuestionnaireCorrection(
  submissionId: string,
): Promise<QuestionnaireSubmission> {
  return apiJson<QuestionnaireSubmission>(
    `/api/v1/questionnaire/submissions/${encodeURIComponent(submissionId)}/request-correction/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    },
  );
}

export function getProjectQuestionnaireConflicts(
  projectId: string,
): Promise<QuestionnaireConflict[]> {
  return apiJson<QuestionnaireConflict[]>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/questionnaire/conflicts/`,
  );
}

export function resolveQuestionnaireConflict(
  conflictId: string,
  request: ResolveQuestionnaireConflictRequest,
): Promise<QuestionnaireConflict> {
  return apiJson<QuestionnaireConflict>(
    `/api/v1/questionnaire/conflicts/${encodeURIComponent(conflictId)}/resolve/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    },
  );
}
