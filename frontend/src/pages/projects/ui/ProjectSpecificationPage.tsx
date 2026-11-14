import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, Navigate, useOutletContext, useParams } from 'react-router';
import { useProject, useProjectMembers } from '../../../entities/project';
import { useSpecification } from '../../../entities/specification';
import type { Specification } from '../../../entities/specification';
import type { User } from '../../../entities/user';
import {
  useSaveSpecification,
  useStartSpecificationGeneration,
} from '../../../features/specification';
import { ApiError } from '../../../shared/api';
import './ProjectSpecificationPage.css';

function formatDate(value: string | null | undefined): string {
  if (!value) return 'Пока недоступно';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    planned: 'Запланирован',
    active: 'Активен',
    blocked: 'Заблокирован',
    completed: 'Завершён',
    cancelled: 'Отменён',
    draft: 'Черновик',
    confirmed: 'Подтверждено',
    rejected: 'Отклонено',
    in_progress: 'В работе',
    todo: 'К выполнению',
    done: 'Выполнено',
    open: 'Открыт',
    resolved: 'Разрешён',
    dismissed: 'Отклонён',
    unresolved: 'Не разрешён',
    archived: 'В архиве',
    pending: 'Ожидает',
    queued: 'В очереди',
    running: 'Выполняется',
    failed: 'Ошибка',
    succeeded: 'Завершён',
    accepted: 'Принято',
    applied: 'Применено',
    discarded: 'Отклонён',
    generated: 'Создано',
    published: 'Опубликовано',
    needs_review: 'Требует проверки',
  };
  return labels[status] ?? status.replaceAll('_', ' ');
}

function generationFailureMessage(errorCode: string): string {
  if (errorCode === 'source_context_too_large') {
    return 'The approved passport and shared Project State exceed the 24,000-byte generation limit. Shorten long text or remove unnecessary detail, then try again.';
  }
  if (errorCode === 'queue_unavailable') {
    return 'Не удалось связаться с обработчиком после нескольких попыток. Текущий черновик сохранён; можно запустить создание заново.';
  }
  return 'Текущий черновик сохранён. Проверьте источники проекта и попробуйте создать его снова.';
}

function useSpecificationDraft(specification: Specification | undefined) {
  const [draft, setDraftState] = useState<string | null>(null);
  const [version, setVersion] = useState<number | null>(null);
  const lastServerContent = useRef<string | null>(null);
  const draftRef = useRef<string | null>(null);

  useEffect(() => {
    if (!specification) return;
    const editorIsPristine =
      draftRef.current === null || draftRef.current === lastServerContent.current;
    if (editorIsPristine) {
      draftRef.current = specification.content;
      setDraftState(specification.content);
      setVersion(specification.version);
    }
    lastServerContent.current = specification.content;
  }, [specification]);

  function setDraft(value: string) {
    draftRef.current = value;
    setDraftState(value);
  }

  function acceptServerVersion(value: Specification) {
    lastServerContent.current = value.content;
    draftRef.current = value.content;
    setDraftState(value.content);
    setVersion(value.version);
  }

  return { draft, setDraft, version, acceptServerVersion };
}

export function ProjectSpecificationPage() {
  const { projectId = '' } = useParams();
  const user = useOutletContext<User>();
  const projectQuery = useProject(projectId);
  const membersQuery = useProjectMembers(projectId);
  const specificationQuery = useSpecification(projectId);
  const saveSpecification = useSaveSpecification(projectId);
  const generateSpecification = useStartSpecificationGeneration(projectId);
  const editor = useSpecificationDraft(specificationQuery.data);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveConflict, setSaveConflict] = useState<
    'stale' | 'project_closed' | 'generation_project_closed' | null
  >(null);
  const [generateMessage, setGenerateMessage] = useState<string | null>(null);

  if (projectQuery.isPending || membersQuery.isPending || specificationQuery.isPending) {
    return (
      <main className="workspace-page">
        <p role="status">Загрузка спецификации проекта…</p>
      </main>
    );
  }

  const loadError = projectQuery.error ?? membersQuery.error ?? specificationQuery.error;
  if (loadError) {
    return (
      <main className="workspace-page">
        <section aria-labelledby="specification-error-title">
          <h1 id="specification-error-title">Не удалось загрузить спецификацию</h1>
          <p role="alert">{loadError.message || 'Проверьте подключение и попробуйте снова.'}</p>
          <button
            className="button button--secondary"
            onClick={() =>
              void Promise.all([
                projectQuery.refetch(),
                membersQuery.refetch(),
                specificationQuery.refetch(),
              ])
            }
            type="button"
          >
            Попробовать снова
          </button>
        </section>
      </main>
    );
  }

  const project = projectQuery.data;
  const specification = specificationQuery.data;
  const member = membersQuery.data?.find((item) => item.user_id === user.id);
  if (!project || !member || !specification) return <Navigate to="/app/projects" replace />;

  const isExecutor = member.role === 'executor';
  const canEdit = isExecutor && (project.status === 'draft' || project.status === 'active');
  const generation = specification.generation;
  const isGenerating = generation?.status === 'queued' || generation?.status === 'running';
  const draft = editor.draft ?? specification.content;
  const version = editor.version ?? specification.version;
  const isDirty = draft !== specification.content;
  const previousGenerationFailed = generation?.status === 'failed';
  const previousGenerationSuperseded = generation?.status === 'superseded';
  const generationDispatchUnavailable =
    generation?.status === 'queued' &&
    ['queue_unavailable', 'worker_backlog'].includes(generation.error_code);

  async function reloadLatest() {
    const result = await specificationQuery.refetch();
    if (result.data) editor.acceptServerVersion(result.data);
    setSaveConflict(null);
    setSaveMessage(null);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canEdit || editor.draft === null || editor.version === null) return;
    setSaveConflict(null);
    setSaveMessage(null);
    saveSpecification.mutate(
      { content: editor.draft, version: editor.version },
      {
        onSuccess: (saved) => {
          editor.acceptServerVersion(saved);
          setSaveConflict(null);
          setSaveMessage(`Saved version ${saved.version}.`);
        },
        onError: async (error) => {
          if (!(error instanceof ApiError) || error.status !== 409) return;
          const [latestProject] = await Promise.all([
            projectQuery.refetch(),
            specificationQuery.refetch(),
          ]);
          const projectIsClosed =
            latestProject.data?.status === 'completed' || latestProject.data?.status === 'archived';
          setSaveConflict(projectIsClosed ? 'project_closed' : 'stale');
        },
      },
    );
  }

  function startGeneration() {
    if (!canEdit || isDirty || isGenerating) return;
    setGenerateMessage(null);
    generateSpecification.mutate(crypto.randomUUID(), {
      onSuccess: (request) => {
        setGenerateMessage(
          request.status === 'queued' || request.status === 'running'
            ? 'Создание поставлено в очередь. Страница обновится, когда черновик будет готов.'
            : `Создание: ${statusLabel(request.status)}.`,
        );
      },
      onError: async (error) => {
        if (!(error instanceof ApiError) || error.status !== 409) return;
        const [latestProject] = await Promise.all([
          projectQuery.refetch(),
          specificationQuery.refetch(),
        ]);
        const projectIsClosed =
          latestProject.data?.status === 'completed' || latestProject.data?.status === 'archived';
        if (projectIsClosed) setSaveConflict('generation_project_closed');
      },
    });
  }

  return (
    <main className="workspace-page project-specification-page">
      <Link className="back-link" to={`/app/projects/${project.id}`}>
        ← К проекту
      </Link>
      <header className="project-specification-heading">
        <div>
          <p className="project-specification-heading__eyebrow">{project.name}</p>
          <h1>Спецификация проекта</h1>
          <p>
            Общий черновик Markdown на основе паспорта и состояния проекта. Неразрешённые вопросы и
            противоречия остаются отмеченными.
          </p>
        </div>
        <span className={`specification-status specification-status--${specification.status}`}>
          {statusLabel(specification.status)} · v{specification.version}
        </span>
      </header>

      {generation && (
        <section
          className={`specification-generation specification-generation--${generation.status}${
            generationDispatchUnavailable ? ' specification-generation--delayed' : ''
          }`}
          aria-live="polite"
        >
          <strong>
            {generationDispatchUnavailable
              ? 'Создание ещё не запущено'
              : isGenerating
                ? generation.status === 'queued'
                  ? 'Ожидание начала создания'
                  : 'Создание спецификации'
                : generation.status === 'failed'
                  ? 'Не удалось создать спецификацию'
                  : generation.status === 'superseded'
                    ? 'Результат создания отклонён'
                    : generation.status === 'succeeded'
                      ? 'Последнее создание завершено'
                      : 'Создание спецификации'}
          </strong>
          <span>
            {generationDispatchUnavailable
              ? 'Создание ожидает обработки. Система продолжит попытки; текущий черновик не изменён.'
              : generation.status === 'queued'
                ? `Request queued ${formatDate(generation.created_at)}. Waiting for a worker.`
                : generation.status === 'failed'
                  ? generationFailureMessage(generation.error_code)
                  : generation.status === 'superseded'
                    ? generation.error_code === 'sources_changed'
                      ? 'Источники проекта изменились во время создания. Запустите создание заново, чтобы использовать актуальные данные.'
                      : 'Черновик изменился во время создания, поэтому результат отклонён.'
                    : generation.status === 'running'
                      ? `Started ${formatDate(generation.started_at)}.`
                      : `Completed ${formatDate(generation.completed_at)}.`}
          </span>
        </section>
      )}

      {generateMessage && (
        <p className="specification-message" role="status">
          {generateMessage}
        </p>
      )}
      {generateSpecification.error && saveConflict !== 'generation_project_closed' && (
        <p className="specification-error" role="alert">
          {generateSpecification.error.message || 'Не удалось запустить создание.'}
        </p>
      )}

      {canEdit ? (
        <section
          className="specification-editor-panel"
          aria-labelledby="specification-editor-title"
        >
          <div className="specification-panel-heading">
            <div>
              <p className="specification-eyebrow">Редактируемый черновик</p>
              <h2 id="specification-editor-title">Текущая спецификация</h2>
            </div>
            <button
              className="button button--secondary"
              disabled={generateSpecification.isPending || isGenerating || isDirty}
              onClick={startGeneration}
              type="button"
            >
              {generateSpecification.isPending || isGenerating ? 'Generating…' : 'Создать черновик'}
            </button>
          </div>

          {isDirty && (
            <p className="specification-hint" role="status">
              Сохраните изменения перед созданием. Будет использована последняя сохранённая версия
              черновика.
            </p>
          )}
          {saveConflict === 'stale' && (
            <section
              className="specification-conflict"
              aria-labelledby="specification-conflict-title"
            >
              <h3 id="specification-conflict-title">Спецификация изменилась на сервере</h3>
              <p>
                Несохранённый текст сохранён на странице. Загрузите последнюю версию перед
                сохранением.
              </p>
              <button
                className="button button--secondary"
                onClick={() => void reloadLatest()}
                type="button"
              >
                Загрузить последнюю версию
              </button>
            </section>
          )}

          <form onSubmit={submit}>
            <label className="specification-editor-label" htmlFor="specification-content">
              Текст Markdown
            </label>
            <textarea
              id="specification-content"
              className="specification-editor"
              maxLength={100_000}
              onChange={(event) => editor.setDraft(event.currentTarget.value)}
              spellCheck
              value={draft}
            />
            <div className="specification-editor-meta">
              <span>Редактируется версия {version}</span>
              <span>{draft.length.toLocaleString()} / 100,000 characters</span>
            </div>
            {saveSpecification.error && saveConflict !== 'stale' && (
              <p className="specification-error" role="alert">
                {saveSpecification.error.message || 'Не удалось сохранить спецификацию.'}
              </p>
            )}
            {saveMessage && (
              <p className="specification-message" role="status">
                {saveMessage}
              </p>
            )}
            <button
              className="button button--primary"
              disabled={!isDirty || saveSpecification.isPending || saveConflict === 'stale'}
              type="submit"
            >
              {saveSpecification.isPending ? 'Saving…' : 'Сохранить спецификацию'}
            </button>
          </form>
          {previousGenerationFailed && !isGenerating && (
            <p className="specification-hint">
              После проверки текущего черновика можно повторить создание.
            </p>
          )}
          {previousGenerationSuperseded && !isGenerating && (
            <p className="specification-hint">
              Создайте спецификацию повторно, чтобы использовать актуальные источники проекта.
            </p>
          )}
        </section>
      ) : (
        <section className="specification-read-panel" aria-labelledby="specification-read-title">
          <div className="specification-panel-heading">
            <div>
              <p className="specification-eyebrow">Общий черновик</p>
              <h2 id="specification-read-title">Текущая спецификация</h2>
            </div>
            {isExecutor && (
              <span className="specification-readonly-note">
                Для закрытых проектов доступен только просмотр
              </span>
            )}
          </div>
          {(saveConflict === 'project_closed' || saveConflict === 'generation_project_closed') && (
            <p className="specification-error" role="alert">
              {saveConflict === 'generation_project_closed'
                ? 'Проект закрыт во время запуска создания. Спецификация доступна только для чтения.'
                : 'Проект закрыт до сохранения изменений. Спецификация доступна только для чтения; несохранённый текст приведён ниже.'}
            </p>
          )}
          {specification.content ? (
            <pre className="specification-content">{specification.content}</pre>
          ) : (
            <p className="specification-empty">Черновик спецификации ещё не создан.</p>
          )}
          {(saveConflict === 'project_closed' || saveConflict === 'generation_project_closed') &&
            isDirty && (
              <div className="specification-unsaved-copy">
                <h3>Ваши несохранённые изменения</h3>
                <pre className="specification-content">{draft}</pre>
              </div>
            )}
        </section>
      )}

      <p className="specification-footer-note">
        Это рабочий черновик без согласования или подписания заказчиком.
      </p>
    </main>
  );
}
