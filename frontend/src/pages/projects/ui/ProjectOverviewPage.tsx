import { useEffect, useState, type FormEvent } from 'react';
import { Link, useOutletContext, useParams } from 'react-router';
import type { User } from '../../../entities/user';
import {
  projectStatusLabels,
  projectTypeOptions,
  useProject,
  useProjectMembers,
  useProjectPassport,
  type Project,
  type ProjectMember,
  type ProjectPassport,
  type ProjectType,
} from '../../../entities/project';
import { InvitationManager } from '../../../features/invitations';
import {
  useProjectLifecycleAction,
  useUpdatePassport,
  useUpdateProject,
  type LifecycleAction,
  type PassportUpdate,
} from '../../../features/projects';
import { ApiError, getApiFieldErrors } from '../../../shared/api';
import { ProjectDocumentsPanel } from './ProjectDocumentsPanel';

type ProjectDraft = {
  name: string;
  project_type: ProjectType;
  description: string;
};

type PassportDraft = {
  goal: string;
  target_audience: string;
  expected_result: string;
  functional_scope: string;
  integrations: string;
  constraints: string;
  deadline: string;
  budget_min: string;
  budget_max: string;
  currency: string;
  additional_data: string;
};

function projectTypeLabel(project: Project): string {
  return (
    projectTypeOptions.find((option) => option.value === project.project_type)?.label ?? 'Other'
  );
}

function toProjectDraft(project: Project): ProjectDraft {
  return {
    name: project.name,
    project_type: project.project_type,
    description: project.description ?? '',
  };
}

function jsonText(value: unknown): string {
  return JSON.stringify(value, null, 2) ?? 'null';
}

function toPassportDraft(passport: ProjectPassport): PassportDraft {
  return {
    goal: passport.goal,
    target_audience: passport.target_audience,
    expected_result: passport.expected_result,
    functional_scope: jsonText(passport.functional_scope),
    integrations: jsonText(passport.integrations),
    constraints: jsonText(passport.constraints),
    deadline: passport.deadline ?? '',
    budget_min: passport.budget_min ?? '',
    budget_max: passport.budget_max ?? '',
    currency: passport.currency ?? '',
    additional_data: jsonText(passport.additional_data),
  };
}

function displayValue(value: string | null | undefined): string {
  return value?.trim() ? value : 'Not provided';
}

function projectActions(
  status: Project['status'],
): Array<{ action: LifecycleAction; label: string }> {
  if (status === 'draft') return [{ action: 'archive', label: 'Archive project' }];
  if (status === 'active') {
    return [
      { action: 'complete', label: 'Complete project' },
      { action: 'archive', label: 'Archive project' },
    ];
  }
  if (status === 'completed') {
    return [
      { action: 'reopen', label: 'Reopen project' },
      { action: 'archive', label: 'Archive project' },
    ];
  }
  return [{ action: 'restore', label: 'Restore project' }];
}

function parseJsonField(
  field: keyof Pick<
    PassportDraft,
    'functional_scope' | 'integrations' | 'constraints' | 'additional_data'
  >,
  value: string,
): unknown {
  try {
    return JSON.parse(value) as unknown;
  } catch {
    throw new Error(`${field.replaceAll('_', ' ')} must contain valid JSON.`);
  }
}

function MemberList({ members }: { members: ProjectMember[] }) {
  return (
    <ul className="member-list">
      {members.map((member) => {
        const fullName = [member.first_name, member.last_name].filter(Boolean).join(' ');
        return (
          <li className="member-row" key={member.id}>
            <span className="member-row__name">
              {fullName || (member.role === 'executor' ? 'Executor' : 'Customer')}
            </span>
            <span className="member-row__role">
              {member.role === 'executor' ? 'Executor' : 'Customer'}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function ProjectMetadata({ project, canEdit }: { project: Project; canEdit: boolean }) {
  const updateProject = useUpdateProject(project.id);
  const [draft, setDraft] = useState<ProjectDraft | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const fieldErrors = getApiFieldErrors(updateProject.error);

  useEffect(() => {
    setDraft(toProjectDraft(project));
  }, [project]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft) return;
    const trimmedName = draft.name.trim();
    if (!trimmedName) {
      setClientError('Enter a project name.');
      return;
    }
    setClientError(null);
    updateProject.mutate(
      {
        name: trimmedName,
        project_type: draft.project_type,
        description: draft.description.trim() || null,
      },
      { onSuccess: (updatedProject) => setDraft(toProjectDraft(updatedProject)) },
    );
  }

  if (!draft) return <p role="status">Loading project details…</p>;

  if (!canEdit) {
    return (
      <dl className="detail-list">
        <div>
          <dt>Project name</dt>
          <dd>{project.name}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{projectTypeLabel(project)}</dd>
        </div>
        <div>
          <dt>Description</dt>
          <dd>{displayValue(project.description)}</dd>
        </div>
      </dl>
    );
  }

  return (
    <form className="detail-form" onSubmit={submit} noValidate>
      <div className="form-field">
        <label htmlFor="overview-name">Project name</label>
        <input
          id="overview-name"
          maxLength={200}
          onChange={(event) => setDraft({ ...draft, name: event.currentTarget.value })}
          value={draft.name}
          aria-invalid={Boolean(fieldErrors.name?.length || clientError)}
          aria-describedby={clientError ? 'overview-name-error' : undefined}
        />
        {clientError && (
          <p className="field-error" id="overview-name-error" role="alert">
            {clientError}
          </p>
        )}
        {fieldErrors.name?.map((message) => (
          <p className="field-error" key={message} role="alert">
            {message}
          </p>
        ))}
      </div>
      <div className="form-field">
        <label htmlFor="overview-type">Project type</label>
        <select
          id="overview-type"
          onChange={(event) =>
            setDraft({ ...draft, project_type: event.currentTarget.value as ProjectType })
          }
          value={draft.project_type}
        >
          {projectTypeOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div className="form-field">
        <label htmlFor="overview-description">
          Description <span>(optional)</span>
        </label>
        <textarea
          id="overview-description"
          onChange={(event) => setDraft({ ...draft, description: event.currentTarget.value })}
          rows={3}
          value={draft.description}
        />
        {fieldErrors.description?.map((message) => (
          <p className="field-error" key={message} role="alert">
            {message}
          </p>
        ))}
      </div>
      {updateProject.error && Object.keys(fieldErrors).length === 0 && (
        <p className="form-error" role="alert">
          {updateProject.error.message ||
            'We couldn’t save these details. Your edits are still here.'}
        </p>
      )}
      <div className="form-actions form-actions--end">
        <button className="button button--primary" disabled={updateProject.isPending} type="submit">
          {updateProject.isPending ? 'Saving…' : 'Save project details'}
        </button>
      </div>
    </form>
  );
}

function PassportPanel({ projectId, canEdit }: { projectId: string; canEdit: boolean }) {
  const passportQuery = useProjectPassport(projectId);
  const updatePassport = useUpdatePassport(projectId);
  const [draft, setDraft] = useState<PassportDraft | null>(null);
  const [draftVersion, setDraftVersion] = useState<number | null>(null);
  const [jsonErrors, setJsonErrors] = useState<Record<string, string>>({});
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const fieldErrors = getApiFieldErrors(updatePassport.error);
  const hasConflict =
    updatePassport.error instanceof ApiError && updatePassport.error.status === 409;

  useEffect(() => {
    if (passportQuery.data && !draft) {
      setDraft(toPassportDraft(passportQuery.data));
      setDraftVersion(passportQuery.data.version);
    }
  }, [passportQuery.data, draft]);

  async function refreshPassport() {
    setRefreshError(null);
    const result = await passportQuery.refetch();
    if (result.isSuccess && result.data) {
      setDraft(toPassportDraft(result.data));
      setDraftVersion(result.data.version);
      setJsonErrors({});
      updatePassport.reset();
    } else {
      setRefreshError('We couldn’t load the latest passport. Your unsaved values are still here.');
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft || draftVersion === null) return;
    const nextJsonErrors: Record<string, string> = {};
    let functionalScope: unknown;
    let integrations: unknown;
    let constraints: unknown;
    let additionalData: unknown;
    try {
      functionalScope = parseJsonField('functional_scope', draft.functional_scope);
    } catch (error) {
      nextJsonErrors.functional_scope = (error as Error).message;
    }
    try {
      integrations = parseJsonField('integrations', draft.integrations);
    } catch (error) {
      nextJsonErrors.integrations = (error as Error).message;
    }
    try {
      constraints = parseJsonField('constraints', draft.constraints);
    } catch (error) {
      nextJsonErrors.constraints = (error as Error).message;
    }
    try {
      additionalData = parseJsonField('additional_data', draft.additional_data);
    } catch (error) {
      nextJsonErrors.additional_data = (error as Error).message;
    }
    setJsonErrors(nextJsonErrors);
    if (Object.keys(nextJsonErrors).length) return;

    const changes: PassportUpdate = {
      version: draftVersion,
      goal: draft.goal,
      target_audience: draft.target_audience,
      expected_result: draft.expected_result,
      functional_scope: functionalScope,
      integrations,
      constraints,
      deadline: draft.deadline || null,
      budget_min: draft.budget_min || null,
      budget_max: draft.budget_max || null,
      currency: draft.currency.trim() || null,
      additional_data: additionalData,
    };
    updatePassport.mutate(changes, {
      onSuccess: (passport) => {
        setDraft(toPassportDraft(passport));
        setDraftVersion(passport.version);
        setJsonErrors({});
        setRefreshError(null);
      },
    });
  }

  if (passportQuery.isPending)
    return (
      <p className="state-message" role="status">
        Loading passport…
      </p>
    );
  if (passportQuery.isError) {
    return (
      <section
        className="state-message state-message--error"
        aria-labelledby="passport-error-title"
      >
        <h3 id="passport-error-title">We couldn’t load the passport</h3>
        <p>{passportQuery.error.message || 'Check your connection and try again.'}</p>
        <button
          className="button button--secondary"
          onClick={() => void passportQuery.refetch()}
          type="button"
        >
          Try again
        </button>
      </section>
    );
  }
  if (!draft)
    return (
      <p className="state-message" role="status">
        Loading passport details…
      </p>
    );

  if (!canEdit) {
    const passport = passportQuery.data;
    return (
      <div className="passport-readonly">
        <p className="passport-version">Version {passport.version}</p>
        <dl className="detail-list detail-list--passport">
          <div>
            <dt>Goal</dt>
            <dd>{displayValue(passport.goal)}</dd>
          </div>
          <div>
            <dt>Target audience</dt>
            <dd>{displayValue(passport.target_audience)}</dd>
          </div>
          <div>
            <dt>Expected result</dt>
            <dd>{displayValue(passport.expected_result)}</dd>
          </div>
          <div>
            <dt>Functional scope</dt>
            <dd>
              <pre>{jsonText(passport.functional_scope)}</pre>
            </dd>
          </div>
          <div>
            <dt>Integrations</dt>
            <dd>
              <pre>{jsonText(passport.integrations)}</pre>
            </dd>
          </div>
          <div>
            <dt>Constraints</dt>
            <dd>
              <pre>{jsonText(passport.constraints)}</pre>
            </dd>
          </div>
          <div>
            <dt>Deadline</dt>
            <dd>{displayValue(passport.deadline)}</dd>
          </div>
          <div>
            <dt>Budget minimum</dt>
            <dd>{displayValue(passport.budget_min)}</dd>
          </div>
          <div>
            <dt>Budget maximum</dt>
            <dd>{displayValue(passport.budget_max)}</dd>
          </div>
          <div>
            <dt>Currency</dt>
            <dd>{displayValue(passport.currency)}</dd>
          </div>
          <div>
            <dt>Additional data</dt>
            <dd>
              <pre>{jsonText(passport.additional_data)}</pre>
            </dd>
          </div>
        </dl>
      </div>
    );
  }

  function changeField<K extends keyof PassportDraft>(field: K, value: PassportDraft[K]) {
    setDraft((current) => (current ? { ...current, [field]: value } : current));
    setJsonErrors((current) => ({ ...current, [field]: '' }));
  }

  return (
    <form className="passport-form" onSubmit={submit} noValidate>
      <p className="passport-version">Version {draftVersion ?? passportQuery.data.version}</p>
      {hasConflict && (
        <div className="conflict-panel" role="alert">
          <div>
            <h3>This passport changed on the server</h3>
            <p>
              Your edits are still here. Reload the latest version only when you’re ready to replace
              them.
            </p>
          </div>
          <button
            className="button button--secondary"
            disabled={passportQuery.isFetching}
            onClick={() => void refreshPassport()}
            type="button"
          >
            {passportQuery.isFetching ? 'Loading…' : 'Reload latest passport'}
          </button>
        </div>
      )}
      {refreshError && (
        <p className="form-error" role="alert">
          {refreshError}
        </p>
      )}
      <div className="passport-fields">
        <div className="form-field">
          <label htmlFor="passport-goal">Goal</label>
          <textarea
            id="passport-goal"
            onChange={(event) => changeField('goal', event.currentTarget.value)}
            rows={3}
            value={draft.goal}
          />
          {fieldErrors.goal?.map((message) => (
            <p className="field-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>
        <div className="form-field">
          <label htmlFor="passport-target-audience">Target audience</label>
          <textarea
            id="passport-target-audience"
            onChange={(event) => changeField('target_audience', event.currentTarget.value)}
            rows={3}
            value={draft.target_audience}
          />
          {fieldErrors.target_audience?.map((message) => (
            <p className="field-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>
        <div className="form-field">
          <label htmlFor="passport-expected-result">Expected result</label>
          <textarea
            id="passport-expected-result"
            onChange={(event) => changeField('expected_result', event.currentTarget.value)}
            rows={3}
            value={draft.expected_result}
          />
          {fieldErrors.expected_result?.map((message) => (
            <p className="field-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>
        <div className="form-field form-field--wide">
          <label htmlFor="passport-functional-scope">
            Functional scope <span>(JSON)</span>
          </label>
          <textarea
            id="passport-functional-scope"
            className="json-input"
            onChange={(event) => changeField('functional_scope', event.currentTarget.value)}
            rows={5}
            value={draft.functional_scope}
          />
          {(jsonErrors.functional_scope || fieldErrors.functional_scope?.[0]) && (
            <p className="field-error" role="alert">
              {jsonErrors.functional_scope || fieldErrors.functional_scope?.[0]}
            </p>
          )}
        </div>
        <div className="form-field form-field--wide">
          <label htmlFor="passport-integrations">
            Integrations <span>(JSON)</span>
          </label>
          <textarea
            id="passport-integrations"
            className="json-input"
            onChange={(event) => changeField('integrations', event.currentTarget.value)}
            rows={4}
            value={draft.integrations}
          />
          {(jsonErrors.integrations || fieldErrors.integrations?.[0]) && (
            <p className="field-error" role="alert">
              {jsonErrors.integrations || fieldErrors.integrations?.[0]}
            </p>
          )}
        </div>
        <div className="form-field form-field--wide">
          <label htmlFor="passport-constraints">
            Constraints <span>(JSON)</span>
          </label>
          <textarea
            id="passport-constraints"
            className="json-input"
            onChange={(event) => changeField('constraints', event.currentTarget.value)}
            rows={4}
            value={draft.constraints}
          />
          {(jsonErrors.constraints || fieldErrors.constraints?.[0]) && (
            <p className="field-error" role="alert">
              {jsonErrors.constraints || fieldErrors.constraints?.[0]}
            </p>
          )}
        </div>
        <div className="form-field">
          <label htmlFor="passport-deadline">Deadline</label>
          <input
            id="passport-deadline"
            onChange={(event) => changeField('deadline', event.currentTarget.value)}
            type="date"
            value={draft.deadline}
          />
          {fieldErrors.deadline?.map((message) => (
            <p className="field-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>
        <div className="form-field">
          <label htmlFor="passport-budget-min">Budget minimum</label>
          <input
            id="passport-budget-min"
            inputMode="decimal"
            onChange={(event) => changeField('budget_min', event.currentTarget.value)}
            type="text"
            value={draft.budget_min}
          />
          {fieldErrors.budget_min?.map((message) => (
            <p className="field-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>
        <div className="form-field">
          <label htmlFor="passport-budget-max">Budget maximum</label>
          <input
            id="passport-budget-max"
            inputMode="decimal"
            onChange={(event) => changeField('budget_max', event.currentTarget.value)}
            type="text"
            value={draft.budget_max}
          />
          {fieldErrors.budget_max?.map((message) => (
            <p className="field-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>
        <div className="form-field">
          <label htmlFor="passport-currency">
            Currency <span>(optional)</span>
          </label>
          <input
            id="passport-currency"
            maxLength={3}
            onChange={(event) => changeField('currency', event.currentTarget.value)}
            type="text"
            value={draft.currency}
          />
          {fieldErrors.currency?.map((message) => (
            <p className="field-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>
        <div className="form-field form-field--wide">
          <label htmlFor="passport-additional-data">
            Additional data <span>(JSON)</span>
          </label>
          <textarea
            id="passport-additional-data"
            className="json-input"
            onChange={(event) => changeField('additional_data', event.currentTarget.value)}
            rows={4}
            value={draft.additional_data}
          />
          {(jsonErrors.additional_data || fieldErrors.additional_data?.[0]) && (
            <p className="field-error" role="alert">
              {jsonErrors.additional_data || fieldErrors.additional_data?.[0]}
            </p>
          )}
        </div>
      </div>
      {updatePassport.error && !hasConflict && Object.keys(fieldErrors).length === 0 && (
        <p className="form-error" role="alert">
          {updatePassport.error.message ||
            'We couldn’t save the passport. Your edits are still here.'}
        </p>
      )}
      <div className="form-actions form-actions--end">
        <button
          className="button button--primary"
          disabled={updatePassport.isPending || hasConflict}
          type="submit"
        >
          {updatePassport.isPending ? 'Saving…' : 'Save passport'}
        </button>
      </div>
    </form>
  );
}

export function ProjectOverviewPage() {
  const user = useOutletContext<User>();
  const { projectId = '' } = useParams();
  const projectQuery = useProject(projectId);
  const membersQuery = useProjectMembers(projectId);
  const lifecycle = useProjectLifecycleAction(projectId);
  const [lifecycleMessage, setLifecycleMessage] = useState<string | null>(null);

  async function retryOverview() {
    await Promise.all([projectQuery.refetch(), membersQuery.refetch()]);
  }

  if (projectQuery.isError || membersQuery.isError) {
    const error = projectQuery.error ?? membersQuery.error;
    return (
      <main className="workspace-page workspace-page--narrow">
        <section
          className="state-message state-message--error"
          aria-labelledby="overview-error-title"
        >
          <h1 id="overview-error-title">We couldn’t open this project</h1>
          <p>
            {error instanceof ApiError && error.status === 404
              ? 'This project is unavailable to your account.'
              : error?.message || 'Check your connection and try again.'}
          </p>
          <div className="form-actions">
            <button
              className="button button--secondary"
              onClick={() => void retryOverview()}
              type="button"
            >
              Try again
            </button>
            <Link className="button button--secondary" to="/app/projects">
              Back to projects
            </Link>
          </div>
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
          Loading project…
        </p>
      </main>
    );
  }

  const project = projectQuery.data;
  const member = membersQuery.data.find((candidate) => candidate.user_id === user.id);
  if (!member) {
    return (
      <main className="workspace-page workspace-page--narrow">
        <section className="state-message state-message--error" role="alert">
          <h1>Project access unavailable</h1>
          <p>Your active project membership could not be confirmed.</p>
          <Link className="button button--secondary" to="/app/projects">
            Back to projects
          </Link>
        </section>
      </main>
    );
  }

  const isExecutor = member.role === 'executor';
  const canEdit = isExecutor && (project.status === 'draft' || project.status === 'active');
  const actions = isExecutor ? projectActions(project.status) : [];

  function runLifecycleAction(action: LifecycleAction) {
    setLifecycleMessage(null);
    lifecycle.mutate(action, {
      onSuccess: () =>
        setLifecycleMessage(`${action[0]?.toUpperCase()}${action.slice(1)} complete.`),
    });
  }

  return (
    <main className="workspace-page">
      <Link
        className="back-link"
        to={project.status === 'archived' ? '/app/projects/archive' : '/app/projects'}
      >
        {project.status === 'archived' ? '← Back to archive' : '← Back to projects'}
      </Link>
      <div className="project-overview-heading">
        <div>
          <p className="project-overview-heading__type">{projectTypeLabel(project)}</p>
          <h1>{project.name}</h1>
          <p className="page-heading__description">
            {project.description?.trim() || 'Project details and passport'}
          </p>
          <Link
            className="button button--secondary project-state-link"
            to={`/app/projects/${project.id}/state`}
          >
            Open Project State
          </Link>
          <Link
            className="button button--secondary project-state-link"
            to={`/app/projects/${project.id}/chat`}
          >
            Open project chat
          </Link>
        </div>
        <span className={`status-badge status-badge--large status-badge--${project.status}`}>
          {projectStatusLabels[project.status]}
        </span>
      </div>

      {lifecycle.error && (
        <p className="form-error" role="alert">
          {lifecycle.error.message || 'The project status could not be changed.'}
        </p>
      )}
      {lifecycleMessage && (
        <p className="success-message" role="status">
          {lifecycleMessage}
        </p>
      )}
      {actions.length > 0 && (
        <section className="lifecycle-actions" aria-label="Project actions">
          {actions.map(({ action, label }) => (
            <button
              className={
                action === 'archive' ? 'button button--secondary' : 'button button--primary'
              }
              disabled={lifecycle.isPending}
              key={action}
              onClick={() => runLifecycleAction(action)}
              type="button"
            >
              {lifecycle.isPending && lifecycle.variables === action ? 'Updating…' : label}
            </button>
          ))}
        </section>
      )}

      {!isExecutor && (
        <section
          className="project-panel questionnaire-entry"
          aria-labelledby="questionnaire-entry-title"
        >
          <div className="section-heading">
            <div>
              <h2 id="questionnaire-entry-title">Customer questionnaire</h2>
              <p className="section-heading__description">
                Share the project details in a guided questionnaire.
              </p>
            </div>
          </div>
          <Link className="button button--primary" to={`/app/projects/${project.id}/questionnaire`}>
            {project.status === 'active' ? 'Open questionnaire' : 'View questionnaire'}
          </Link>
        </section>
      )}

      <div className="overview-grid">
        <div className="overview-column">
          <section className="project-panel" aria-labelledby="project-details-title">
            <div className="section-heading">
              <h2 id="project-details-title">Project details</h2>
              {canEdit && <span className="section-heading__note">Executor can edit</span>}
            </div>
            <ProjectMetadata project={project} canEdit={canEdit} />
          </section>

          <section className="project-panel" aria-labelledby="participants-title">
            <div className="section-heading">
              <h2 id="participants-title">Participants</h2>
              <span className="section-heading__note">Active members</span>
            </div>
            <MemberList members={membersQuery.data} />
          </section>
          {isExecutor && <InvitationManager projectId={project.id} canManage={canEdit} />}
        </div>

        <section className="project-panel passport-panel" aria-labelledby="passport-title">
          <div className="section-heading">
            <div>
              <h2 id="passport-title">Project passport</h2>
              <p className="section-heading__description">
                {canEdit
                  ? 'Keep the project brief current as you prepare the work.'
                  : 'Shared project information for both participants.'}
              </p>
            </div>
            {!canEdit && <span className="section-heading__note">Read only</span>}
          </div>
          <PassportPanel projectId={project.id} canEdit={canEdit} />
        </section>
      </div>
      <ProjectDocumentsPanel
        canUpload={project.status === 'draft' || project.status === 'active'}
        projectId={project.id}
      />
    </main>
  );
}
