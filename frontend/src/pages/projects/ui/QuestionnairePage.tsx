import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useOutletContext, useParams } from 'react-router';
import { useProject, useProjectMembers } from '../../../entities/project';
import {
  useProjectQuestionnaire,
  type QuestionnaireAnswer,
  type QuestionnaireAnswers,
  type QuestionnaireQuestion,
  type QuestionnaireValue,
} from '../../../entities/questionnaire';
import type { User } from '../../../entities/user';
import {
  useSaveQuestionnaireDraft,
  useStartQuestionnaireDraft,
} from '../../../features/questionnaire';
import { ApiError, getApiFieldErrors } from '../../../shared/api';

type VisibilityCondition = { question: string; equals: unknown };
type SelectOption = { value: string; label: string };

function questionCondition(question: QuestionnaireQuestion): VisibilityCondition | null {
  const condition = question.visible_if;
  if (!condition || typeof condition !== 'object' || Array.isArray(condition)) return null;
  const candidate = condition as Record<string, unknown>;
  if (typeof candidate.question !== 'string' || !('equals' in candidate)) return null;
  return { question: candidate.question, equals: candidate.equals };
}

function questionIsVisible(
  question: QuestionnaireQuestion,
  answers: QuestionnaireAnswers,
): boolean {
  const condition = questionCondition(question);
  return condition === null || answers[condition.question] === condition.equals;
}

function toQuestionnaireValue(value: unknown): QuestionnaireValue | undefined {
  if (
    value === null ||
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return value;
  }
  if (Array.isArray(value) && value.every((item) => typeof item === 'string')) return value;
  return undefined;
}

function answersFromSubmission(answers: QuestionnaireAnswer[] | undefined): QuestionnaireAnswers {
  return Object.fromEntries(
    (answers ?? []).flatMap((answer) => {
      const value = toQuestionnaireValue(answer.value);
      return value === undefined ? [] : [[answer.question_key, value]];
    }),
  );
}

function editedAnswers(
  answers: QuestionnaireAnswers,
  editedKeys: Set<string>,
): QuestionnaireAnswers {
  return Object.fromEntries(
    [...editedKeys].flatMap((key) => (Object.hasOwn(answers, key) ? [[key, answers[key]]] : [])),
  );
}

function questionOptions(question: QuestionnaireQuestion): SelectOption[] {
  return (question.options ?? []).flatMap((option) => {
    if (!option || typeof option !== 'object' || Array.isArray(option)) return [];
    const candidate = option as Record<string, unknown>;
    if (typeof candidate.value !== 'string' || typeof candidate.label !== 'string') return [];
    return [{ value: candidate.value, label: candidate.label }];
  });
}

function fieldValue(
  question: QuestionnaireQuestion,
  value: QuestionnaireValue | undefined,
): string {
  if (question.type === 'boolean') {
    return typeof value === 'boolean' ? String(value) : '';
  }
  if (question.type === 'string_list') {
    return Array.isArray(value) ? value.join('\n') : '';
  }
  return value === null || value === undefined ? '' : String(value);
}

function fieldInputType(question: QuestionnaireQuestion): string {
  if (question.type === 'url') return 'url';
  if (question.type === 'date') return 'date';
  if (question.type === 'decimal') return 'number';
  return 'text';
}

function fieldErrorsFor(error: unknown, fieldErrors: Record<string, string[]>): string[] {
  if (fieldErrors.error) return fieldErrors.error;
  if (error instanceof ApiError && fieldErrors.non_field_errors?.length) {
    return fieldErrors.non_field_errors;
  }
  return [];
}

function projectTypeLabel(projectType: string): string {
  const label = projectType.replaceAll('_', ' ');
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`;
}

export function QuestionnairePage() {
  const user = useOutletContext<User>();
  const { projectId = '' } = useParams();
  const projectQuery = useProject(projectId);
  const membersQuery = useProjectMembers(projectId);
  const questionnaireQuery = useProjectQuestionnaire(projectId);
  const startDraft = useStartQuestionnaireDraft(projectId);
  const submissionId = questionnaireQuery.data?.submission?.id ?? '';
  const saveDraft = useSaveQuestionnaireDraft(projectId, submissionId);
  const [answers, setAnswers] = useState<QuestionnaireAnswers>({});
  const [editedKeys, setEditedKeys] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setAnswers(answersFromSubmission(questionnaireQuery.data?.submission?.answers));
    setEditedKeys(new Set());
  }, [questionnaireQuery.data?.submission]);

  const schema = questionnaireQuery.data?.schema;
  const questions = schema?.questions ?? [];
  const visibleQuestions = useMemo(
    () => questions.filter((question) => questionIsVisible(question, answers)),
    [answers, questions],
  );
  const serverAnswers = questionnaireQuery.data?.submission?.answers ?? [];
  const serverAnswerByKey = new Map(serverAnswers.map((answer) => [answer.question_key, answer]));
  const fieldErrors = getApiFieldErrors(saveDraft.error);
  const loadError = projectQuery.error ?? membersQuery.error ?? questionnaireQuery.error;
  const hasLoadError = projectQuery.isError || membersQuery.isError || questionnaireQuery.isError;
  const isLoading =
    projectQuery.isPending || membersQuery.isPending || questionnaireQuery.isPending;

  async function retryLoad() {
    await Promise.all([
      projectQuery.refetch(),
      membersQuery.refetch(),
      questionnaireQuery.refetch(),
    ]);
  }

  function changeAnswer(questionKey: string, value: QuestionnaireValue | undefined) {
    const nextValue = value === undefined ? null : value;
    setAnswers((current) => {
      const updated = { ...current };
      updated[questionKey] = nextValue;

      for (const question of questions) {
        const condition = questionCondition(question);
        if (condition && condition.question === questionKey && nextValue !== condition.equals) {
          delete updated[question.key];
        }
      }
      if (questionKey === 'has_integrations' && nextValue === false) {
        updated.integrations = [];
      }
      return updated;
    });
    setEditedKeys((current) => {
      const updated = new Set(current).add(questionKey);
      for (const question of questions) {
        const condition = questionCondition(question);
        if (condition && condition.question === questionKey && nextValue !== condition.equals) {
          updated.delete(question.key);
        }
      }
      return updated;
    });
    saveDraft.reset();
    startDraft.reset();
  }

  function renderQuestion(question: QuestionnaireQuestion) {
    const currentValue = answers[question.key];
    const htmlId = `questionnaire-${question.key}`;
    const messages = fieldErrorsFor(saveDraft.error, fieldErrors).length
      ? fieldErrorsFor(saveDraft.error, fieldErrors)
      : (fieldErrors[question.key] ?? []);
    const serverAnswer = serverAnswerByKey.get(question.key);
    const origin = editedKeys.has(question.key) ? 'customer' : serverAnswer?.origin;

    function updateText(value: string) {
      if (question.type === 'decimal') {
        changeAnswer(question.key, value === '' ? undefined : value);
      } else if (question.type === 'string_list') {
        changeAnswer(
          question.key,
          value
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean),
        );
      } else {
        changeAnswer(question.key, value);
      }
    }

    return (
      <div className="form-field questionnaire-field" key={question.key}>
        <label htmlFor={htmlId}>
          {question.label}
          {question.required && <span> (required)</span>}
          {!question.required && <span> (optional)</span>}
        </label>
        {origin === 'prefilled' && <p className="questionnaire-origin">From passport</p>}
        {origin === 'customer' && serverAnswer?.origin === 'prefilled' && (
          <p className="questionnaire-origin">Entered by you</p>
        )}
        {question.type === 'textarea' || question.type === 'string_list' ? (
          <textarea
            id={htmlId}
            aria-invalid={messages.length > 0}
            aria-required={question.required}
            aria-describedby={messages.length ? `${htmlId}-error` : undefined}
            minLength={question.min_length}
            maxLength={question.max_length}
            onChange={(event) => updateText(event.currentTarget.value)}
            rows={question.type === 'string_list' ? 4 : 3}
            value={fieldValue(question, currentValue)}
          />
        ) : question.type === 'boolean' ? (
          <select
            id={htmlId}
            aria-invalid={messages.length > 0}
            aria-required={question.required}
            onChange={(event) =>
              changeAnswer(
                question.key,
                event.currentTarget.value === '' ? undefined : event.currentTarget.value === 'true',
              )
            }
            value={fieldValue(question, currentValue)}
          >
            <option value="">Choose yes or no</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        ) : question.type === 'select' ? (
          <select
            id={htmlId}
            aria-invalid={messages.length > 0}
            aria-required={question.required}
            onChange={(event) => changeAnswer(question.key, event.currentTarget.value || undefined)}
            value={fieldValue(question, currentValue)}
          >
            <option value="">Choose an option</option>
            {questionOptions(question).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        ) : (
          <input
            id={htmlId}
            aria-invalid={messages.length > 0}
            aria-required={question.required}
            aria-describedby={messages.length ? `${htmlId}-error` : undefined}
            minLength={question.min_length}
            maxLength={question.max_length}
            min={question.minimum}
            onChange={(event) => updateText(event.currentTarget.value)}
            step={question.type === 'decimal' ? 'any' : undefined}
            type={fieldInputType(question)}
            value={fieldValue(question, currentValue)}
          />
        )}
        {messages.length > 0 && (
          <p className="field-error" id={`${htmlId}-error`} role="alert">
            {messages.join(' ')}
          </p>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <main className="workspace-page">
        <p className="state-message" role="status">
          Loading questionnaire...
        </p>
      </main>
    );
  }

  if (hasLoadError || !projectQuery.data || !membersQuery.data || !questionnaireQuery.data) {
    return (
      <main className="workspace-page workspace-page--narrow">
        <section
          className="state-message state-message--error"
          aria-labelledby="questionnaire-error-title"
        >
          <h1 id="questionnaire-error-title">We couldn't load the questionnaire</h1>
          <p>{loadError?.message || 'Check your connection and try again.'}</p>
          <button
            className="button button--secondary"
            onClick={() => void retryLoad()}
            type="button"
          >
            Try again
          </button>
        </section>
      </main>
    );
  }

  const member = membersQuery.data.find((candidate) => candidate.user_id === user.id);
  if (!member) {
    return (
      <main className="workspace-page workspace-page--narrow">
        <section className="state-message state-message--error" role="alert">
          <h1>Questionnaire access unavailable</h1>
          <p>Your active project membership could not be confirmed.</p>
        </section>
      </main>
    );
  }

  const submission = questionnaireQuery.data.submission;
  const isCustomer = member.role === 'customer';
  const canEdit =
    isCustomer && projectQuery.data.status === 'active' && submission?.status === 'draft';
  const canStart = isCustomer && projectQuery.data.status === 'active' && !submission;

  function save(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (submission) saveDraft.mutate(editedAnswers(answers, editedKeys));
  }

  return (
    <main className="workspace-page workspace-page--narrow questionnaire-page">
      <Link className="back-link" to={`/app/projects/${projectId}`}>
        Back to project
      </Link>
      <div className="page-heading">
        <div>
          <p className="project-overview-heading__type">
            {projectTypeLabel(questionnaireQuery.data.schema.project_type)}
          </p>
          <h1>Customer questionnaire</h1>
          <p className="page-heading__description">
            {projectTypeLabel(questionnaireQuery.data.schema.project_type)} · version{' '}
            {questionnaireQuery.data.schema.version}
          </p>
        </div>
      </div>

      {submission ? (
        <p className="questionnaire-status" role="status">
          Draft questionnaire
        </p>
      ) : (
        <p className="questionnaire-empty">No draft has been started yet.</p>
      )}

      {canStart && (
        <section className="project-panel questionnaire-panel">
          {startDraft.error && (
            <p className="form-error" role="alert">
              {startDraft.error.message}
            </p>
          )}
          <button
            className="button button--primary"
            disabled={startDraft.isPending}
            onClick={() => startDraft.mutate()}
            type="button"
          >
            {startDraft.isPending
              ? 'Starting...'
              : startDraft.isError
                ? 'Try again'
                : 'Start questionnaire'}
          </button>
        </section>
      )}

      {submission && canEdit && (
        <form className="project-panel questionnaire-panel" onSubmit={save} noValidate>
          <p className="questionnaire-help">
            Your draft is saved separately from the project passport. You can return to it later.
          </p>
          {visibleQuestions.map(renderQuestion)}
          {saveDraft.error && (
            <p className="form-error" role="alert">
              {saveDraft.error.message ||
                "We couldn't save this draft. Your answers are still here."}
            </p>
          )}
          {saveDraft.isSuccess && (
            <p className="success-message" role="status">
              Draft saved.
            </p>
          )}
          <div className="form-actions form-actions--end">
            {saveDraft.isError && (
              <button
                className="button button--secondary"
                disabled={saveDraft.isPending}
                onClick={() => save()}
                type="button"
              >
                Try save again
              </button>
            )}
            <button
              className="button button--primary"
              disabled={saveDraft.isPending || editedKeys.size === 0}
              type="submit"
            >
              {saveDraft.isPending ? 'Saving...' : 'Save draft'}
            </button>
          </div>
        </form>
      )}

      {!canEdit && submission && (
        <section className="project-panel questionnaire-panel">
          <p>
            {isCustomer
              ? 'This project is read-only. The questionnaire draft is available for viewing.'
              : 'The customer can edit this questionnaire draft.'}
          </p>
          <dl className="questionnaire-summary">
            {submission.answers.map((answer) => (
              <div key={answer.question_key}>
                <dt>
                  {questions.find((question) => question.key === answer.question_key)?.label ??
                    answer.question_key}
                </dt>
                <dd>
                  {Array.isArray(answer.value) ? answer.value.join(', ') : String(answer.value)}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {isCustomer && !canStart && !submission && (
        <p className="state-message">
          A questionnaire draft can be started when the project is active.
        </p>
      )}
      {!isCustomer && !submission && (
        <p className="questionnaire-empty">
          The customer has not started a questionnaire draft yet.
        </p>
      )}
    </main>
  );
}
