import type { components } from '../../../shared/api/generated/schema';

export type ProjectQuestionnaire = components['schemas']['ProjectQuestionnaireResponse'];
export type QuestionnaireSchema = components['schemas']['QuestionnaireSchemaResponse'];
export type QuestionnaireQuestion = components['schemas']['QuestionnaireQuestionSchema'];
export type QuestionnaireSubmission = components['schemas']['QuestionnaireSubmissionResponse'];
export type QuestionnaireAnswer = components['schemas']['QuestionnaireAnswerResponse'];

export type QuestionnaireValue = string | number | boolean | string[] | null;

export type QuestionnaireAnswers = Record<string, QuestionnaireValue>;

export const questionnaireQueryKeys = {
  all: ['questionnaire'] as const,
  project: (projectId: string) => [...questionnaireQueryKeys.all, projectId] as const,
};
