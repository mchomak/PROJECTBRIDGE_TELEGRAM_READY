import { useRef, useState, type FormEvent } from 'react';
import { Link, Navigate, useOutletContext, useParams } from 'react-router';
import {
  useAIAnalysisRequests,
  useAIProposals,
  type AIAnalysisRequest,
  type AIProposal,
} from '../../../entities/ai-analysis';
import { useProject, useProjectMembers } from '../../../entities/project';
import type { User } from '../../../entities/user';
import {
  useAcceptAIProposal,
  useApplyEditedAIProposal,
  useRefreshAIProposalsWhenAnalysisCompletes,
  useRejectAIProposal,
  useStartManualAIAnalysis,
} from '../../../features/ai-analysis';
import { ApiError } from '../../../shared/api';
import './ProjectAIPage.css';

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function formatDate(value: string | null | undefined): string {
  if (!value) return 'Not available yet';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}

function statusLabel(status: string): string {
  return status.replaceAll('_', ' ');
}

function requestLabel(request: AIAnalysisRequest): string {
  if (request.status === 'failed') return request.error_code || 'Analysis failed';
  if (request.status === 'succeeded') {
    return `${request.result_count} ${request.result_count === 1 ? 'proposal' : 'proposals'}`;
  }
  return request.status === 'queued' ? 'Waiting to start' : 'Analysis in progress';
}

function dispatchWarning(request: AIAnalysisRequest): string | null {
  if (
    request.status !== 'queued' ||
    !['queue_unavailable', 'worker_backlog'].includes(request.error_code)
  ) {
    return null;
  }
  return 'This analysis is waiting for processing. The system will keep retrying; it has not started yet.';
}

function sourceLabel(sourceType: string): string {
  const labels: Record<string, string> = {
    questionnaire_answer: 'Questionnaire answer',
    message: 'Chat message',
    document_chunk: 'Document excerpt',
    passport: 'Project passport',
  };
  return labels[sourceType] ?? 'Project source';
}

function sourceDetails(proposal: AIProposal, sourceId: string): string[] {
  const source = proposal.evidence.find((evidence) => evidence.source_id === sourceId);
  if (!source || !isObject(source.metadata)) return [];
  const details: string[] = [];
  if (typeof source.metadata.filename === 'string') details.push(source.metadata.filename);
  if (typeof source.metadata.page_number === 'number') {
    details.push(`Page ${source.metadata.page_number}`);
  }
  if (typeof source.metadata.question_key === 'string') {
    details.push(source.metadata.question_key.replaceAll('_', ' '));
  }
  return details;
}

function AnalysisHistory({ requests }: { requests: AIAnalysisRequest[] }) {
  return (
    <section aria-labelledby="ai-history-title" className="ai-history">
      <div className="ai-section-heading">
        <div>
          <p className="ai-eyebrow">Recent activity</p>
          <h2 id="ai-history-title">Analysis history</h2>
        </div>
        <span className="ai-count">{requests.length}</span>
      </div>
      {requests.length === 0 ? (
        <p className="ai-empty-inline">No analyses have been started for this project.</p>
      ) : (
        <ol className="ai-history-list">
          {requests.map((request) => (
            <li className="ai-history-row" key={request.id}>
              <span
                className={`ai-status-dot ai-status-dot--${request.status}`}
                aria-hidden="true"
              />
              <div className="ai-history-row__body">
                <div className="ai-history-row__topline">
                  <strong>{statusLabel(request.status)}</strong>
                  <time dateTime={request.created_at}>{formatDate(request.created_at)}</time>
                </div>
                <p>{requestLabel(request)}</p>
                {dispatchWarning(request) && (
                  <p className="ai-dispatch-warning" role="status">
                    {dispatchWarning(request)}
                  </p>
                )}
                {request.run && (
                  <p className="ai-run-meta">
                    {request.run.model_name} · {request.run.input_tokens ?? '—'} input tokens ·{' '}
                    {request.run.estimated_cost
                      ? `$${request.run.estimated_cost}`
                      : 'cost unavailable'}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function ProposalCard({ proposal, projectId }: { proposal: AIProposal; projectId: string }) {
  const accept = useAcceptAIProposal(projectId, proposal.id);
  const reject = useRejectAIProposal(projectId, proposal.id);
  const applyEdited = useApplyEditedAIProposal(projectId, proposal.id);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(() => JSON.stringify(proposal.proposed_payload, null, 2));
  const [draftError, setDraftError] = useState<string | null>(null);
  const canReview = proposal.status === 'pending';
  const actionError = accept.error ?? reject.error ?? applyEdited.error;

  function submitEdited(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    let payload: unknown;
    try {
      payload = JSON.parse(draft) as unknown;
    } catch {
      setDraftError('Enter valid JSON before applying this edit.');
      return;
    }
    if (!isObject(payload)) {
      setDraftError('The edited payload must be a JSON object.');
      return;
    }
    setDraftError(null);
    applyEdited.mutate(payload, { onSuccess: () => setEditing(false) });
  }

  return (
    <article className="ai-proposal-card" aria-labelledby={`proposal-${proposal.id}`}>
      <div className="ai-proposal-card__header">
        <div>
          <p className="ai-eyebrow">{statusLabel(proposal.proposal_type)}</p>
          <h3 id={`proposal-${proposal.id}`}>{proposal.title}</h3>
        </div>
        <span className={`ai-proposal-status ai-proposal-status--${proposal.status}`}>
          {statusLabel(proposal.status)}
        </span>
      </div>
      {proposal.description && <p className="ai-proposal-description">{proposal.description}</p>}
      {proposal.rationale && (
        <div className="ai-rationale">
          <strong>Why it was suggested</strong>
          <p>{proposal.rationale}</p>
        </div>
      )}
      <section aria-label="Proposal evidence" className="ai-evidence-list">
        <h4>Evidence</h4>
        {proposal.evidence.length === 0 ? (
          <p className="ai-empty-inline">This proposal has no linked source excerpts.</p>
        ) : (
          proposal.evidence.map((evidence) => (
            <figure className="ai-evidence" key={evidence.id}>
              <figcaption>
                <span>{sourceLabel(evidence.source_type)}</span>
                <code>{evidence.source_id}</code>
                {sourceDetails(proposal, evidence.source_id).map((detail) => (
                  <span className="ai-evidence__detail" key={detail}>
                    {detail}
                  </span>
                ))}
              </figcaption>
              <blockquote>{evidence.excerpt}</blockquote>
            </figure>
          ))
        )}
      </section>
      {canReview && (
        <div className="ai-proposal-actions">
          {editing ? (
            <form className="ai-edit-form" onSubmit={submitEdited}>
              <label htmlFor={`payload-${proposal.id}`}>Edit proposed Project State data</label>
              <textarea
                id={`payload-${proposal.id}`}
                rows={8}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                spellCheck={false}
              />
              {draftError && (
                <p className="form-error" role="alert">
                  {draftError}
                </p>
              )}
              {applyEdited.error && (
                <p className="form-error" role="alert">
                  {applyEdited.error.message || 'The edited proposal could not be applied.'}
                </p>
              )}
              <div className="ai-action-buttons">
                <button
                  className="button button--primary"
                  disabled={applyEdited.isPending}
                  type="submit"
                >
                  {applyEdited.isPending ? 'Applying…' : 'Apply edited proposal'}
                </button>
                <button
                  className="button button--quiet"
                  onClick={() => setEditing(false)}
                  type="button"
                >
                  Cancel edit
                </button>
              </div>
            </form>
          ) : (
            <>
              {actionError && (
                <p className="form-error" role="alert">
                  {actionError.message ||
                    'This proposal could not be updated. Review the evidence and try again.'}
                </p>
              )}
              <div className="ai-action-buttons">
                <button
                  className="button button--primary"
                  disabled={accept.isPending || reject.isPending}
                  onClick={() => accept.mutate()}
                  type="button"
                >
                  {accept.isPending ? 'Applying…' : 'Accept and apply'}
                </button>
                <button
                  className="button button--secondary"
                  disabled={accept.isPending || reject.isPending}
                  onClick={() => setEditing(true)}
                  type="button"
                >
                  Edit first
                </button>
                <button
                  className="button button--quiet"
                  disabled={accept.isPending || reject.isPending}
                  onClick={() => reject.mutate()}
                  type="button"
                >
                  {reject.isPending ? 'Rejecting…' : 'Reject'}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </article>
  );
}

export function ProjectAIPage() {
  const user = useOutletContext<User>();
  const { projectId = '' } = useParams();
  const projectQuery = useProject(projectId);
  const membersQuery = useProjectMembers(projectId);
  const member = membersQuery.data?.find((candidate) => candidate.user_id === user.id);
  const isExecutor = member?.role === 'executor';
  const requestsQuery = useAIAnalysisRequests(projectId, isExecutor);
  const proposalsQuery = useAIProposals(projectId, isExecutor);
  useRefreshAIProposalsWhenAnalysisCompletes(projectId, requestsQuery.data);
  const start = useStartManualAIAnalysis(projectId);
  const retryKey = useRef<string | null>(null);
  const hasActiveRequest = requestsQuery.data?.some(
    (request) => request.status === 'queued' || request.status === 'running',
  );

  function startAnalysis() {
    const idempotencyKey =
      retryKey.current ??
      globalThis.crypto?.randomUUID?.() ??
      `analysis-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    retryKey.current = idempotencyKey;
    start.mutate(idempotencyKey, { onSuccess: () => (retryKey.current = null) });
  }

  async function retryWorkspace() {
    await Promise.all([
      projectQuery.refetch(),
      membersQuery.refetch(),
      ...(isExecutor ? [requestsQuery.refetch(), proposalsQuery.refetch()] : []),
    ]);
  }

  if (projectQuery.isError || membersQuery.isError) {
    const error = projectQuery.error ?? membersQuery.error;
    return (
      <main className="workspace-page workspace-page--narrow">
        <section
          className="state-message state-message--error"
          aria-labelledby="ai-page-error-title"
        >
          <h1 id="ai-page-error-title">We couldn’t open AI review</h1>
          <p>
            {error instanceof ApiError && error.status === 404
              ? 'This project is unavailable to your account.'
              : error?.message || 'Check your connection and try again.'}
          </p>
          <button
            className="button button--secondary"
            onClick={() => void retryWorkspace()}
            type="button"
          >
            Try again
          </button>
        </section>
      </main>
    );
  }

  if (
    projectQuery.isPending ||
    membersQuery.isPending ||
    !projectQuery.data ||
    !membersQuery.data
  ) {
    return (
      <main className="workspace-page">
        <p className="state-message" role="status">
          Loading AI review…
        </p>
      </main>
    );
  }

  if (!member) {
    return (
      <main className="workspace-page workspace-page--narrow">
        <p className="state-message state-message--error" role="alert">
          Your active project membership could not be confirmed.
        </p>
      </main>
    );
  }

  if (!isExecutor) return <Navigate to={`/app/projects/${projectId}`} replace />;

  const dataError = requestsQuery.error ?? proposalsQuery.error;
  const isLoading = requestsQuery.isPending || proposalsQuery.isPending;
  const requests = requestsQuery.data ?? [];
  const proposals = proposalsQuery.data ?? [];
  const pendingProposals = proposals.filter((proposal) => proposal.status === 'pending');

  return (
    <main className="workspace-page project-ai-page">
      <Link className="back-link" to={`/app/projects/${projectId}`}>
        ← Back to project
      </Link>
      <header className="project-ai-heading">
        <div>
          <p className="ai-eyebrow">Executor workspace</p>
          <h1>AI analysis and proposals</h1>
          <p>
            Start an analysis when you need one. Suggestions remain private until you review and
            apply them.
          </p>
        </div>
        <button
          className="button button--primary"
          disabled={start.isPending || hasActiveRequest}
          onClick={startAnalysis}
          type="button"
        >
          {start.isPending
            ? 'Starting analysis…'
            : hasActiveRequest
              ? 'Analysis in progress'
              : 'Analyze project'}
        </button>
      </header>
      <p className="ai-manual-note">
        Analyses run only when you start them. Project messages, questionnaire answers, and
        documents do not start one automatically.
      </p>
      {start.error && (
        <div className="ai-page-alert" role="alert">
          <p>{start.error.message || 'The analysis request could not be queued.'}</p>
          <button className="button button--secondary" onClick={startAnalysis} type="button">
            Retry this request
          </button>
        </div>
      )}
      {dataError && (
        <div className="ai-page-alert" role="alert">
          <p>{dataError.message || 'AI review data could not be loaded.'}</p>
          <button
            className="button button--secondary"
            onClick={() => void retryWorkspace()}
            type="button"
          >
            Try again
          </button>
        </div>
      )}
      <div className="project-ai-layout">
        <AnalysisHistory requests={requests} />
        <section aria-labelledby="ai-proposals-title" className="ai-inbox">
          <div className="ai-section-heading">
            <div>
              <p className="ai-eyebrow">Review before applying</p>
              <h2 id="ai-proposals-title">Proposal inbox</h2>
            </div>
            <span className="ai-count">{pendingProposals.length} pending</span>
          </div>
          {isLoading ? (
            <p className="ai-empty-inline" role="status">
              Loading proposals…
            </p>
          ) : proposals.length === 0 ? (
            <div className="ai-empty-state">
              <span aria-hidden="true" className="ai-empty-state__mark">
                ✦
              </span>
              <h3>No proposals to review</h3>
              <p>
                When an analysis finds a supported change or possible conflict, it will appear here
                with its source evidence.
              </p>
            </div>
          ) : (
            <div className="ai-proposal-list">
              {proposals.map((proposal) => (
                <ProposalCard key={proposal.id} proposal={proposal} projectId={projectId} />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
