import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useOutletContext, useParams } from 'react-router';
import { useProject, useProjectMembers, useProjectPassport } from '../../../entities/project';
import {
  useProjectQuestionnaire,
  useProjectQuestionnaireConflicts,
  type QuestionnaireAnswer,
  type QuestionnaireAnswers,
  type QuestionnaireConflict,
  type QuestionnaireQuestion,
  type QuestionnaireValue,
} from '../../../entities/questionnaire';
import type { User } from '../../../entities/user';
import {
  useRefreshQuestionnaireDraftPassportVersion,
  useRequestQuestionnaireCorrection,
  useResolveQuestionnaireConflict,
  useSaveQuestionnaireDraft,
  useStartQuestionnaireDraft,
  useSubmitQuestionnaire,
} from '../../../features/questionnaire';
import { ApiError, getApiFieldErrors } from '../../../shared/api';
import {
  questionnaireOptionLabel,
  questionnaireQuestionLabel,
} from '../../../shared/i18n/questionnaire';

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
  const labels: Record<string, string> = {
    website: 'Сайт',
    telegram_bot: 'Telegram-бот',
    automation: 'Автоматизация',
    other: 'Другое',
  };
  return labels[projectType] ?? 'Другой тип проекта';
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Не указано';
  if (typeof value === 'boolean') return value ? 'Да' : 'Нет';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function conflictFieldLabel(conflict: QuestionnaireConflict): string {
  const labels: Record<string, string> = {
    goal: 'Цель проекта',
    target_audience: 'Целевая аудитория',
    expected_result: 'Ожидаемый результат',
    functional_scope: 'Функциональность',
    integrations: 'Интеграции',
    constraints: 'Ограничения',
    deadline: 'Срок',
    budget_min: 'Минимальный бюджет',
    budget_max: 'Максимальный бюджет',
    currency: 'Валюта',
  };
  const field = conflict.mapped_field.split('.').at(-1) ?? conflict.mapped_field;
  return labels[field] ?? 'Поле паспорта';
}

export function QuestionnairePage() {
  const user = useOutletContext<User>();
  const { projectId = '' } = useParams();
  const projectQuery = useProject(projectId);
  const membersQuery = useProjectMembers(projectId);
  const member = membersQuery.data?.find((candidate) => candidate.user_id === user.id);
  const isExecutor = member?.role === 'executor';
  const questionnaireQuery = useProjectQuestionnaire(projectId);
  const conflictsQuery = useProjectQuestionnaireConflicts(projectId, isExecutor);
  const passportQuery = useProjectPassport(projectId, isExecutor);
  const startDraft = useStartQuestionnaireDraft(projectId);
  const submissionId = questionnaireQuery.data?.submission?.id ?? '';
  const saveDraft = useSaveQuestionnaireDraft(projectId, submissionId);
  const submitSubmission = useSubmitQuestionnaire(projectId, submissionId);
  const refreshDraftVersion = useRefreshQuestionnaireDraftPassportVersion(projectId, submissionId);
  const requestCorrection = useRequestQuestionnaireCorrection(projectId, submissionId);
  const resolveConflict = useResolveQuestionnaireConflict(projectId);
  const [answers, setAnswers] = useState<QuestionnaireAnswers>({});
  const [editedKeys, setEditedKeys] = useState<Set<string>>(() => new Set());
  const [confirmPrefilled, setConfirmPrefilled] = useState(false);

  useEffect(() => {
    setAnswers(answersFromSubmission(questionnaireQuery.data?.submission?.answers));
    setEditedKeys(new Set());
    setConfirmPrefilled(false);
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
  const submitFieldErrors = getApiFieldErrors(submitSubmission.error);
  const stalePassportVersionError =
    submitSubmission.error instanceof ApiError &&
    submitSubmission.error.status === 409 &&
    submitSubmission.error.payload?.detail.includes('passport changed after this draft started');
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
    refreshDraftVersion.reset();
  }

  function displayConflictValue(value: unknown, questionKey: string): string {
    const question = questions.find((item) => item.key === questionKey);
    if (question?.type === 'select' && typeof value === 'string') {
      return questionnaireOptionLabel(
        schema?.schema_key ?? '',
        schema?.version ?? 0,
        questionKey,
        value,
        value,
      );
    }
    return displayValue(value);
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
          {questionnaireQuestionLabel(
            schema?.schema_key ?? '',
            schema?.version ?? 0,
            question.key,
            question.label,
          )}
          {question.required && <span> (обязательно)</span>}
          {!question.required && <span> (необязательно)</span>}
        </label>
        {origin === 'prefilled' && <p className="questionnaire-origin">Из паспорта</p>}
        {origin === 'customer' && serverAnswer?.origin === 'prefilled' && (
          <p className="questionnaire-origin">Введено вами</p>
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
            aria-describedby={messages.length ? `${htmlId}-error` : undefined}
            onChange={(event) =>
              changeAnswer(
                question.key,
                event.currentTarget.value === '' ? undefined : event.currentTarget.value === 'true',
              )
            }
            value={fieldValue(question, currentValue)}
          >
            <option value="">Выберите да или нет</option>
            <option value="true">Да</option>
            <option value="false">Нет</option>
          </select>
        ) : question.type === 'select' ? (
          <select
            id={htmlId}
            aria-invalid={messages.length > 0}
            aria-required={question.required}
            aria-describedby={messages.length ? `${htmlId}-error` : undefined}
            onChange={(event) => changeAnswer(question.key, event.currentTarget.value || undefined)}
            value={fieldValue(question, currentValue)}
          >
            <option value="">Выберите вариант</option>
            {questionOptions(question).map((option) => (
              <option key={option.value} value={option.value}>
                {questionnaireOptionLabel(
                  schema?.schema_key ?? '',
                  schema?.version ?? 0,
                  question.key,
                  option.value,
                  option.label,
                )}
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
          Загрузка анкеты...
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
          <h1 id="questionnaire-error-title">Не удалось загрузить анкету</h1>
          <p>{loadError?.message || 'Проверьте подключение и попробуйте снова.'}</p>
          <button
            className="button button--secondary"
            onClick={() => void retryLoad()}
            type="button"
          >
            Попробовать снова
          </button>
        </section>
      </main>
    );
  }

  if (!member) {
    return (
      <main className="workspace-page workspace-page--narrow">
        <section className="state-message state-message--error" role="alert">
          <h1>Нет доступа к анкете</h1>
          <p>Не удалось подтвердить ваше участие в проекте.</p>
        </section>
      </main>
    );
  }

  const submission = questionnaireQuery.data.submission;
  const isCustomer = member.role === 'customer';
  const canEdit =
    isCustomer && projectQuery.data.status === 'active' && submission?.status === 'draft';
  const canStart = isCustomer && projectQuery.data.status === 'active' && !submission;
  const unconfirmedPrefills = serverAnswers.some(
    (answer) => answer.origin === 'prefilled' && !answer.is_confirmed,
  );
  const canSubmit = canEdit && (!unconfirmedPrefills || confirmPrefilled) && !saveDraft.isPending;

  function save(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (submission) saveDraft.mutate(editedAnswers(answers, editedKeys));
  }

  async function submit() {
    if (!submission) return;
    try {
      if (editedKeys.size > 0) {
        await saveDraft.mutateAsync(editedAnswers(answers, editedKeys));
      }
      await submitSubmission.mutateAsync({ confirm_prefilled: confirmPrefilled });
    } catch {
      // The mutations retain their errors for the form's recovery message.
    }
  }

  function resolve(conflict: QuestionnaireConflict, decision: 'keep_passport' | 'apply_answer') {
    const expectedVersion = passportQuery.data?.version;
    if (!expectedVersion) return;
    resolveConflict.mutate({
      conflictId: conflict.id,
      request: { decision, expected_passport_version: expectedVersion },
    });
  }

  return (
    <main className="workspace-page workspace-page--narrow questionnaire-page">
      <Link className="back-link" to={`/app/projects/${projectId}`}>
        К проекту
      </Link>
      <div className="page-heading">
        <div>
          <p className="project-overview-heading__type">
            {projectTypeLabel(questionnaireQuery.data.schema.project_type)}
          </p>
          <h1>Анкета заказчика</h1>
          <p className="page-heading__description">
            {projectTypeLabel(questionnaireQuery.data.schema.project_type)} · версия{' '}
            {questionnaireQuery.data.schema.version}
          </p>
        </div>
      </div>

      {submission ? (
        <p className="questionnaire-status" role="status">
          {submission.status === 'submitted'
            ? 'Отправленная анкета'
            : submission.supersedes_id
              ? 'Черновик исправлений'
              : submission.status === 'correction_requested'
                ? 'Запрошены исправления'
                : 'Черновик анкеты'}
        </p>
      ) : (
        <p className="questionnaire-empty">Черновик ещё не создан.</p>
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
              ? 'Начало...'
              : startDraft.isError
                ? 'Попробовать снова'
                : 'Заполнить анкету'}
          </button>
        </section>
      )}

      {submission && canEdit && (
        <form className="project-panel questionnaire-panel" onSubmit={save} noValidate>
          <p className="questionnaire-help">
            Черновик сохраняется отдельно от паспорта проекта. К нему можно вернуться позже.
          </p>
          {visibleQuestions.map(renderQuestion)}
          {saveDraft.error && (
            <p className="form-error" role="alert">
              {saveDraft.error.message ||
                'Не удалось сохранить черновик. Ваши ответы сохранены на странице.'}
            </p>
          )}
          {saveDraft.isSuccess && (
            <p className="success-message" role="status">
              Черновик сохранён.
            </p>
          )}
          {unconfirmedPrefills && (
            <label className="questionnaire-confirmation">
              <input
                checked={confirmPrefilled}
                onChange={(event) => setConfirmPrefilled(event.currentTarget.checked)}
                type="checkbox"
              />
              <span>Я проверил и подтверждаю ответы, заполненные из паспорта.</span>
            </label>
          )}
          {submitSubmission.error && (
            <div className="form-error" role="alert">
              <p>
                {stalePassportVersionError
                  ? 'Паспорт проекта изменился после создания черновика. Обновите версию, проверьте ответы и отправьте их снова.'
                  : submitSubmission.error.message || 'Не удалось отправить анкету.'}
              </p>
              {stalePassportVersionError && (
                <button
                  className="button button--secondary"
                  disabled={refreshDraftVersion.isPending}
                  onClick={() => {
                    submitSubmission.reset();
                    refreshDraftVersion.mutate();
                  }}
                  type="button"
                >
                  {refreshDraftVersion.isPending ? 'Обновление...' : 'Обновить версию черновика'}
                </button>
              )}
            </div>
          )}
          {refreshDraftVersion.error && (
            <p className="form-error" role="alert">
              {refreshDraftVersion.error.message || 'Не удалось обновить черновик.'}
            </p>
          )}
          {refreshDraftVersion.isSuccess && (
            <p className="success-message" role="status">
              Версия черновика обновлена. Проверьте ответы и отправьте их снова.
            </p>
          )}
          {submitFieldErrors.confirm_prefilled?.length ? (
            <p className="form-error" role="alert">
              {submitFieldErrors.confirm_prefilled.join(' ')}
            </p>
          ) : null}
          <div className="form-actions form-actions--end">
            {saveDraft.isError && (
              <button
                className="button button--secondary"
                disabled={saveDraft.isPending}
                onClick={() => save()}
                type="button"
              >
                Повторить сохранение
              </button>
            )}
            <button
              className="button button--primary"
              disabled={saveDraft.isPending || editedKeys.size === 0}
              type="submit"
            >
              {saveDraft.isPending ? 'Сохранение...' : 'Сохранить черновик'}
            </button>
            <button
              className="button button--primary"
              disabled={!canSubmit || submitSubmission.isPending}
              onClick={() => void submit()}
              type="button"
            >
              {submitSubmission.isPending ? 'Отправка...' : 'Отправить ответы'}
            </button>
          </div>
        </form>
      )}

      {!canEdit && submission && (
        <section className="project-panel questionnaire-panel">
          <p>
            {submission.status === 'submitted'
              ? 'Ответы отправлены и заблокированы для изменений.'
              : isCustomer
                ? 'Проект доступен только для чтения. Анкету можно просмотреть.'
                : submission.supersedes_id
                  ? 'Заказчик может редактировать этот черновик исправлений.'
                  : 'Заказчик может редактировать этот черновик анкеты.'}
          </p>
          <dl className="questionnaire-summary">
            {submission.answers.map((answer) => (
              <div key={answer.question_key}>
                <dt>
                  {questionnaireQuestionLabel(
                    schema?.schema_key ?? '',
                    schema?.version ?? 0,
                    answer.question_key,
                    questions.find((question) => question.key === answer.question_key)?.label ??
                      answer.question_key,
                  )}
                </dt>
                <dd>
                  {typeof answer.value === 'boolean'
                    ? answer.value
                      ? 'Да'
                      : 'Нет'
                    : typeof answer.value === 'string' &&
                        questions.find((question) => question.key === answer.question_key)?.type ===
                          'select'
                      ? questionnaireOptionLabel(
                          schema?.schema_key ?? '',
                          schema?.version ?? 0,
                          answer.question_key,
                          answer.value,
                          answer.value,
                        )
                      : Array.isArray(answer.value)
                        ? answer.value.join(', ')
                        : String(answer.value)}
                </dd>
              </div>
            ))}
          </dl>
          {isExecutor &&
            submission.status === 'submitted' &&
            projectQuery.data.status === 'active' && (
              <div className="form-actions form-actions--end">
                {requestCorrection.error && (
                  <p className="form-error" role="alert">
                    {requestCorrection.error.message}
                  </p>
                )}
                {requestCorrection.isSuccess && (
                  <p className="success-message" role="status">
                    Запрошен черновик исправлений.
                  </p>
                )}
                <button
                  className="button button--secondary"
                  disabled={requestCorrection.isPending}
                  onClick={() => requestCorrection.mutate()}
                  type="button"
                >
                  {requestCorrection.isPending ? 'Отправка запроса...' : 'Запросить исправления'}
                </button>
              </div>
            )}
        </section>
      )}

      {questionnaireQuery.data.history.length > 1 && (
        <section
          className="project-panel questionnaire-panel"
          aria-labelledby="questionnaire-history-title"
        >
          <h2 id="questionnaire-history-title">История анкеты</h2>
          <ol className="questionnaire-history">
            {questionnaireQuery.data.history.map((version) => (
              <li key={version.id}>
                <span>
                  {version.status === 'correction_requested'
                    ? 'Запрошены исправления'
                    : version.status === 'submitted'
                      ? 'Отправлена'
                      : version.supersedes_id
                        ? 'Черновик исправлений'
                        : 'Черновик'}
                </span>
                <time dateTime={version.started_at}>
                  {new Date(version.started_at).toLocaleDateString()}
                </time>
              </li>
            ))}
          </ol>
        </section>
      )}

      {isExecutor && (
        <section
          className="project-panel questionnaire-panel"
          aria-labelledby="questionnaire-conflicts-title"
        >
          <h2 id="questionnaire-conflicts-title">Противоречия в анкете</h2>
          {conflictsQuery.isPending && (
            <p className="questionnaire-help">Загрузка противоречий...</p>
          )}
          {conflictsQuery.isError && (
            <div className="form-error" role="alert">
              <p>{conflictsQuery.error.message}</p>
              <button
                className="button button--secondary"
                onClick={() => void conflictsQuery.refetch()}
                type="button"
              >
                Попробовать снова
              </button>
            </div>
          )}
          {resolveConflict.error && (
            <div className="form-error" role="alert">
              <p>{resolveConflict.error.message}</p>
              <button
                className="button button--secondary"
                onClick={() =>
                  void Promise.all([passportQuery.refetch(), conflictsQuery.refetch()])
                }
                type="button"
              >
                Обновить паспорт и противоречия
              </button>
            </div>
          )}
          {!conflictsQuery.isPending && !conflictsQuery.isError && !conflictsQuery.data?.length && (
            <p className="questionnaire-empty">Неразрешённых противоречий в анкете нет.</p>
          )}
          {conflictsQuery.data?.map((conflict) => (
            <article className="questionnaire-conflict" key={conflict.id}>
              <h3>{conflictFieldLabel(conflict)}</h3>
              <dl className="questionnaire-summary">
                <div>
                  <dt>Текущее значение в паспорте</dt>
                  <dd>{displayConflictValue(conflict.passport_value, conflict.question_key)}</dd>
                </div>
                <div>
                  <dt>Ответ заказчика</dt>
                  <dd>{displayConflictValue(conflict.answer_value, conflict.question_key)}</dd>
                </div>
              </dl>
              <div className="form-actions">
                <button
                  className="button button--secondary"
                  disabled={resolveConflict.isPending || !passportQuery.data}
                  onClick={() => resolve(conflict, 'keep_passport')}
                  type="button"
                >
                  Оставить значение паспорта
                </button>
                <button
                  className="button button--primary"
                  disabled={resolveConflict.isPending || !passportQuery.data}
                  onClick={() => resolve(conflict, 'apply_answer')}
                  type="button"
                >
                  Применить ответ анкеты
                </button>
              </div>
            </article>
          ))}
        </section>
      )}

      {isCustomer && !canStart && !submission && (
        <p className="state-message">Анкету можно начать заполнять, когда проект активен.</p>
      )}
      {!isCustomer && !submission && (
        <p className="questionnaire-empty">Заказчик ещё не начал заполнять анкету.</p>
      )}
    </main>
  );
}
