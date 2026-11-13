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
  if (!value) return 'Not available yet';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

function statusLabel(status: string): string {
  return status.replaceAll('_', ' ');
}

function generationFailureMessage(errorCode: string): string {
  if (errorCode === 'source_context_too_large') {
    return 'The approved passport and shared Project State exceed the 24,000-byte generation limit. Shorten long text or remove unnecessary detail, then try again.';
  }
  if (errorCode === 'queue_unavailable') {
    return 'The generation worker could not be reached after several attempts. Your current draft was kept; you can start a new generation.';
  }
  return 'The current draft was kept. Review the project sources and try generation again.';
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
        <p role="status">Loading project specification…</p>
      </main>
    );
  }

  const loadError = projectQuery.error ?? membersQuery.error ?? specificationQuery.error;
  if (loadError) {
    return (
      <main className="workspace-page">
        <section aria-labelledby="specification-error-title">
          <h1 id="specification-error-title">We couldn’t load the specification</h1>
          <p role="alert">{loadError.message || 'Check your connection and try again.'}</p>
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
            Try again
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
            ? 'Generation queued. This page will update when the draft is ready.'
            : `Generation ${statusLabel(request.status)}.`,
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
        ← Back to project
      </Link>
      <header className="project-specification-heading">
        <div>
          <p className="project-specification-heading__eyebrow">{project.name}</p>
          <h1>Project specification</h1>
          <p>
            One shared Markdown draft built from the project passport and shared Project State.
            Unresolved questions and conflicts remain clearly marked.
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
              ? 'Generation has not started'
              : isGenerating
                ? generation.status === 'queued'
                  ? 'Waiting for generation to start'
                  : 'Generating specification'
                : generation.status === 'failed'
                  ? 'Generation failed'
                  : generation.status === 'superseded'
                    ? 'Generation discarded'
                    : generation.status === 'succeeded'
                      ? 'Latest generation completed'
                      : 'Specification generation'}
          </strong>
          <span>
            {generationDispatchUnavailable
              ? 'This generation is waiting for processing. The system will keep retrying; the current draft is unchanged.'
              : generation.status === 'queued'
                ? `Request queued ${formatDate(generation.created_at)}. Waiting for a worker.`
                : generation.status === 'failed'
                  ? generationFailureMessage(generation.error_code)
                  : generation.status === 'superseded'
                    ? generation.error_code === 'sources_changed'
                      ? 'Project sources changed while generation was queued or running. Start a new generation to use the latest sources.'
                      : 'The current draft changed during generation, so its result was discarded.'
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
          {generateSpecification.error.message || 'Generation could not be started.'}
        </p>
      )}

      {canEdit ? (
        <section
          className="specification-editor-panel"
          aria-labelledby="specification-editor-title"
        >
          <div className="specification-panel-heading">
            <div>
              <p className="specification-eyebrow">Editable draft</p>
              <h2 id="specification-editor-title">Current specification</h2>
            </div>
            <button
              className="button button--secondary"
              disabled={generateSpecification.isPending || isGenerating || isDirty}
              onClick={startGeneration}
              type="button"
            >
              {generateSpecification.isPending || isGenerating ? 'Generating…' : 'Generate draft'}
            </button>
          </div>

          {isDirty && (
            <p className="specification-hint" role="status">
              Save your edits before starting generation. Generation uses the latest saved draft
              version.
            </p>
          )}
          {saveConflict === 'stale' && (
            <section
              className="specification-conflict"
              aria-labelledby="specification-conflict-title"
            >
              <h3 id="specification-conflict-title">This specification changed on the server</h3>
              <p>Your unsaved text is still here. Reload the latest version before saving again.</p>
              <button
                className="button button--secondary"
                onClick={() => void reloadLatest()}
                type="button"
              >
                Reload latest version
              </button>
            </section>
          )}

          <form onSubmit={submit}>
            <label className="specification-editor-label" htmlFor="specification-content">
              Markdown content
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
              <span>Editing version {version}</span>
              <span>{draft.length.toLocaleString()} / 100,000 characters</span>
            </div>
            {saveSpecification.error && saveConflict !== 'stale' && (
              <p className="specification-error" role="alert">
                {saveSpecification.error.message || 'The specification could not be saved.'}
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
              {saveSpecification.isPending ? 'Saving…' : 'Save specification'}
            </button>
          </form>
          {previousGenerationFailed && !isGenerating && (
            <p className="specification-hint">
              You can retry generation after reviewing the current draft.
            </p>
          )}
          {previousGenerationSuperseded && !isGenerating && (
            <p className="specification-hint">Generate again to use the current project sources.</p>
          )}
        </section>
      ) : (
        <section className="specification-read-panel" aria-labelledby="specification-read-title">
          <div className="specification-panel-heading">
            <div>
              <p className="specification-eyebrow">Shared draft</p>
              <h2 id="specification-read-title">Current specification</h2>
            </div>
            {isExecutor && (
              <span className="specification-readonly-note">Read-only for closed projects</span>
            )}
          </div>
          {(saveConflict === 'project_closed' || saveConflict === 'generation_project_closed') && (
            <p className="specification-error" role="alert">
              {saveConflict === 'generation_project_closed'
                ? 'This project closed while generation was starting. The specification is now read-only.'
                : 'This project closed before your edit could be saved. The specification is now read-only; your unsaved text is preserved below.'}
            </p>
          )}
          {specification.content ? (
            <pre className="specification-content">{specification.content}</pre>
          ) : (
            <p className="specification-empty">No specification draft has been created yet.</p>
          )}
          {(saveConflict === 'project_closed' || saveConflict === 'generation_project_closed') &&
            isDirty && (
              <div className="specification-unsaved-copy">
                <h3>Your unsaved edits</h3>
                <pre className="specification-content">{draft}</pre>
              </div>
            )}
        </section>
      )}

      <p className="specification-footer-note">
        This is a working draft. It has no customer approval or signature workflow.
      </p>
    </main>
  );
}
