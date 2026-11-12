import { useState, type FormEvent } from 'react';
import { Link, useOutletContext, useParams } from 'react-router';
import type { components } from '../../../shared/api/generated/schema';
import { useProject, useProjectMembers } from '../../../entities/project';
import {
  useProjectStateAggregate,
  useProjectStateCollection,
  useProjectStateEvidenceOptions,
  type EvidenceOption,
  type OpenQuestion,
  type ProjectConflict,
  type ProjectStage,
  type ProjectTask,
  type Requirement,
} from '../../../entities/project-state';
import type { User } from '../../../entities/user';
import {
  useCreateProjectStateRecord,
  useUpdateProjectStateRecord,
} from '../../../features/project-state';
import { ApiError } from '../../../shared/api';

type StageCreate = components['schemas']['ProjectStageCreate'];
type RequirementCreate = components['schemas']['RequirementCreate'];
type TaskCreate = components['schemas']['TaskCreate'];
type OpenQuestionCreate = components['schemas']['OpenQuestionCreate'];
type ProjectConflictCreate = components['schemas']['ProjectConflictCreate'];
type StagePatch = components['schemas']['PatchedProjectStagePatch'];
type RequirementPatch = components['schemas']['PatchedRequirementPatch'];
type TaskPatch = components['schemas']['PatchedTaskPatch'];
type OpenQuestionPatch = components['schemas']['PatchedOpenQuestionPatch'];
type ProjectConflictPatch = components['schemas']['PatchedProjectConflictPatch'];

const transitionOptions = {
  stage: {
    planned: ['active', 'cancelled'],
    active: ['blocked', 'completed', 'cancelled'],
    blocked: ['active', 'cancelled'],
  },
  requirement: {
    draft: ['confirmed', 'rejected'],
    confirmed: ['in_progress', 'rejected'],
    in_progress: ['blocked', 'completed', 'rejected'],
    blocked: ['in_progress', 'rejected'],
  },
  task: {
    todo: ['in_progress', 'cancelled'],
    in_progress: ['blocked', 'done', 'cancelled'],
    blocked: ['in_progress', 'cancelled'],
  },
  open_question: { open: ['resolved', 'dismissed'] },
  conflict: { unresolved: ['resolved', 'dismissed'] },
} satisfies Record<string, Record<string, string[]>>;

function statusText(status: string): string {
  return status.replaceAll('_', ' ');
}

function nextStatuses(graph: Record<string, string[]>, current: string): string[] {
  return graph[current] ?? [];
}

function evidenceQuestionLabel(metadata: unknown): string {
  if (metadata && typeof metadata === 'object' && 'question_key' in metadata) {
    const questionKey = (metadata as { question_key?: unknown }).question_key;
    if (typeof questionKey === 'string') return questionKey.replaceAll('_', ' ');
  }
  return 'Questionnaire answer';
}

function TransitionField({
  current,
  options,
  label,
  value,
  onChange,
}: {
  current: string;
  options: string[];
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  if (options.length === 0) {
    return <p className="project-state__terminal">Status: {statusText(current)}</p>;
  }
  return (
    <label className="form-field" htmlFor={label}>
      Status
      <select id={label} value={value} onChange={(event) => onChange(event.currentTarget.value)}>
        <option value={current}>{statusText(current)}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {statusText(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function StageCard({
  stage,
  canEdit,
  save,
}: {
  stage: ProjectStage;
  canEdit: boolean;
  save: (id: string, changes: StagePatch, done: () => void) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(stage.name);
  const [description, setDescription] = useState(stage.description);
  const [position, setPosition] = useState(String(stage.position));
  const [startDate, setStartDate] = useState(stage.start_date ?? '');
  const [dueDate, setDueDate] = useState(stage.due_date ?? '');
  const [nextStatus, setNextStatus] = useState(stage.status);
  const options = nextStatuses(transitionOptions.stage, stage.status);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    save(
      stage.id,
      {
        name: name.trim(),
        description: description.trim(),
        position: Number(position),
        start_date: startDate || null,
        due_date: dueDate || null,
        ...(nextStatus === stage.status ? {} : { status: nextStatus as StagePatch['status'] }),
      },
      () => setEditing(false),
    );
  }

  return (
    <article className="project-state__record">
      <div className="project-state__record-heading">
        <h3>{stage.name}</h3>
        <span className="project-state__status">{statusText(stage.status)}</span>
      </div>
      {stage.description && <p>{stage.description}</p>}
      <p className="project-state__dates">
        {stage.start_date ? `Starts ${stage.start_date}` : 'Start date not set'}
        {' · '}
        {stage.due_date ? `Due ${stage.due_date}` : 'Due date not set'}
      </p>
      {canEdit && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          Edit stage
        </button>
      )}
      {canEdit && editing && (
        <form className="project-state__editor" onSubmit={submit}>
          <label className="form-field">
            Stage name
            <input
              required
              maxLength={200}
              value={name}
              onChange={(event) => setName(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Description
            <textarea
              rows={2}
              value={description}
              onChange={(event) => setDescription(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Position
            <input
              min={0}
              type="number"
              value={position}
              onChange={(event) => setPosition(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Start date
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Due date
            <input
              type="date"
              value={dueDate}
              onChange={(event) => setDueDate(event.currentTarget.value)}
            />
          </label>
          <TransitionField
            current={stage.status}
            label={`stage-status-${stage.id}`}
            onChange={(value) => setNextStatus(value as typeof stage.status)}
            options={options}
            value={nextStatus}
          />
          <div className="form-actions">
            <button className="button button--primary" type="submit">
              Save stage
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </article>
  );
}

function RequirementCard({
  requirement,
  canEdit,
  save,
}: {
  requirement: Requirement;
  canEdit: boolean;
  save: (id: string, changes: RequirementPatch, done: () => void) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(requirement.title);
  const [description, setDescription] = useState(requirement.description);
  const [nextStatus, setNextStatus] = useState(requirement.status);
  const options = nextStatuses(transitionOptions.requirement, requirement.status);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    save(
      requirement.id,
      {
        title: title.trim(),
        description: description.trim(),
        ...(nextStatus === requirement.status
          ? {}
          : { status: nextStatus as RequirementPatch['status'] }),
      },
      () => setEditing(false),
    );
  }

  return (
    <article className="project-state__record">
      <div className="project-state__record-heading">
        <h3>{requirement.title}</h3>
        <span className="project-state__status">{statusText(requirement.status)}</span>
      </div>
      {requirement.description && <p>{requirement.description}</p>}
      {requirement.confirmed_at && (
        <p className="project-state__dates">
          Confirmed {new Date(requirement.confirmed_at).toLocaleDateString()}
        </p>
      )}
      {canEdit && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          Edit requirement
        </button>
      )}
      {canEdit && editing && (
        <form className="project-state__editor" onSubmit={submit}>
          <label className="form-field">
            Requirement
            <input
              required
              maxLength={255}
              value={title}
              onChange={(event) => setTitle(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Description
            <textarea
              rows={2}
              value={description}
              onChange={(event) => setDescription(event.currentTarget.value)}
            />
          </label>
          <TransitionField
            current={requirement.status}
            label={`requirement-status-${requirement.id}`}
            onChange={(value) => setNextStatus(value as typeof requirement.status)}
            options={options}
            value={nextStatus}
          />
          <div className="form-actions">
            <button className="button button--primary" type="submit">
              Save requirement
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </article>
  );
}

function TaskCard({
  task,
  stages,
  members,
  canEdit,
  save,
}: {
  task: ProjectTask;
  stages: ProjectStage[];
  members: Array<{
    id: string;
    user_id: string;
    role: string;
    first_name: string;
    last_name: string;
  }>;
  canEdit: boolean;
  save: (id: string, changes: TaskPatch, done: () => void) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);
  const [stageId, setStageId] = useState(task.stage_id ?? '');
  const [assigneeId, setAssigneeId] = useState(task.assignee_id ?? '');
  const [dueDate, setDueDate] = useState(task.due_date ?? '');
  const [nextStatus, setNextStatus] = useState(task.status);
  const options = nextStatuses(transitionOptions.task, task.status);
  const assignedMember = members.find((member) => member.user_id === task.assignee_id);
  const assignedName = assignedMember
    ? [assignedMember.first_name, assignedMember.last_name].filter(Boolean).join(' ') ||
      assignedMember.role
    : null;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    save(
      task.id,
      {
        title: title.trim(),
        description: description.trim(),
        stage_id: stageId || null,
        assignee_id: assigneeId || null,
        due_date: dueDate || null,
        ...(nextStatus === task.status ? {} : { status: nextStatus as TaskPatch['status'] }),
      },
      () => setEditing(false),
    );
  }

  return (
    <article className="project-state__record">
      <div className="project-state__record-heading">
        <h3>{task.title}</h3>
        <span className="project-state__status">{statusText(task.status)}</span>
      </div>
      {task.description && <p>{task.description}</p>}
      <p className="project-state__dates">
        {task.due_date ? `Due ${task.due_date}` : 'Due date not set'}
        {assignedName ? ` · Assigned to ${assignedName}` : ''}
      </p>
      {task.stage_id && (
        <p className="project-state__dates">
          Stage: {stages.find((stage) => stage.id === task.stage_id)?.name ?? 'Unavailable'}
        </p>
      )}
      {canEdit && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          Edit task
        </button>
      )}
      {canEdit && editing && (
        <form className="project-state__editor" onSubmit={submit}>
          <label className="form-field">
            Task
            <input
              required
              maxLength={255}
              value={title}
              onChange={(event) => setTitle(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Description
            <textarea
              rows={2}
              value={description}
              onChange={(event) => setDescription(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Stage
            <select value={stageId} onChange={(event) => setStageId(event.currentTarget.value)}>
              <option value="">No stage</option>
              {stages.map((stage) => (
                <option key={stage.id} value={stage.id}>
                  {stage.name}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            Assignee
            <select
              value={assigneeId}
              onChange={(event) => setAssigneeId(event.currentTarget.value)}
            >
              <option value="">Unassigned</option>
              {members.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {[member.first_name, member.last_name].filter(Boolean).join(' ') || member.role}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            Due date
            <input
              type="date"
              value={dueDate}
              onChange={(event) => setDueDate(event.currentTarget.value)}
            />
          </label>
          <TransitionField
            current={task.status}
            label={`task-status-${task.id}`}
            onChange={(value) => setNextStatus(value as typeof task.status)}
            options={options}
            value={nextStatus}
          />
          <div className="form-actions">
            <button className="button button--primary" type="submit">
              Save task
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </article>
  );
}

function OpenQuestionCard({
  item,
  canEdit,
  save,
}: {
  item: OpenQuestion;
  canEdit: boolean;
  save: (id: string, changes: OpenQuestionPatch, done: () => void) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [question, setQuestion] = useState(item.question);
  const [answer, setAnswer] = useState(item.answer);
  const [nextStatus, setNextStatus] = useState(item.status);
  const options = nextStatuses(transitionOptions.open_question, item.status);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    save(
      item.id,
      {
        question: question.trim(),
        answer: answer.trim(),
        ...(nextStatus === item.status
          ? {}
          : { status: nextStatus as OpenQuestionPatch['status'] }),
      },
      () => setEditing(false),
    );
  }

  return (
    <article className="project-state__record">
      <div className="project-state__record-heading">
        <h3>{item.question}</h3>
        <span className="project-state__status">{statusText(item.status)}</span>
      </div>
      {item.answer && <p>{item.answer}</p>}
      {item.resolved_at && (
        <p className="project-state__dates">
          Closed {new Date(item.resolved_at).toLocaleDateString()}
        </p>
      )}
      {canEdit && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          Edit question
        </button>
      )}
      {canEdit && editing && (
        <form className="project-state__editor" onSubmit={submit}>
          <label className="form-field">
            Question
            <textarea
              required
              rows={2}
              value={question}
              onChange={(event) => setQuestion(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Answer
            <textarea
              rows={2}
              value={answer}
              onChange={(event) => setAnswer(event.currentTarget.value)}
            />
          </label>
          <TransitionField
            current={item.status}
            label={`question-status-${item.id}`}
            onChange={(value) => setNextStatus(value as typeof item.status)}
            options={options}
            value={nextStatus}
          />
          <div className="form-actions">
            <button className="button button--primary" type="submit">
              Save question
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </article>
  );
}

function ProjectConflictCard({
  conflict,
  canEdit,
  save,
}: {
  conflict: ProjectConflict;
  canEdit: boolean;
  save: (id: string, changes: ProjectConflictPatch, done: () => void) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [nextStatus, setNextStatus] = useState(conflict.status);
  const [resolution, setResolution] = useState(conflict.resolution);
  const options = nextStatuses(transitionOptions.conflict, conflict.status);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    save(
      conflict.id,
      {
        ...(nextStatus === conflict.status
          ? {}
          : { status: nextStatus as ProjectConflictPatch['status'] }),
        resolution: resolution.trim(),
      },
      () => setEditing(false),
    );
  }

  return (
    <article className="project-state__record">
      <div className="project-state__record-heading">
        <h3>{conflict.title}</h3>
        <span className="project-state__status">{statusText(conflict.status)}</span>
      </div>
      {conflict.description && <p>{conflict.description}</p>}
      {conflict.resolution && (
        <p>
          <strong>Resolution:</strong> {conflict.resolution}
        </p>
      )}
      <ul className="project-state__evidence">
        {conflict.evidence.map((evidence) => (
          <li key={evidence.id}>
            <span>{evidenceQuestionLabel(evidence.metadata)}:</span> {evidence.excerpt}
          </li>
        ))}
      </ul>
      {conflict.resolved_at && (
        <p className="project-state__dates">
          Decided {new Date(conflict.resolved_at).toLocaleDateString()}
        </p>
      )}
      {canEdit && conflict.status === 'unresolved' && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          {options.length > 0 ? 'Resolve conflict' : 'Edit conflict'}
        </button>
      )}
      {canEdit && conflict.status === 'unresolved' && editing && (
        <form className="project-state__editor" onSubmit={submit}>
          <TransitionField
            current={conflict.status}
            label={`conflict-status-${conflict.id}`}
            onChange={(value) => setNextStatus(value as typeof conflict.status)}
            options={options}
            value={nextStatus}
          />
          <label className="form-field">
            Resolution
            <textarea
              required={nextStatus === 'resolved'}
              rows={3}
              value={resolution}
              onChange={(event) => setResolution(event.currentTarget.value)}
            />
          </label>
          <div className="form-actions">
            <button className="button button--primary" type="submit">
              Save conflict
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </article>
  );
}

function EmptyMessage({ canEdit, entity }: { canEdit: boolean; entity: string }) {
  return (
    <p className="project-state__empty">
      {canEdit
        ? `Add the first ${entity} to the shared project plan.`
        : `The executor has not added any ${entity} yet.`}
    </p>
  );
}

function SectionHeader({ title, count }: { title: string; count: number }) {
  return (
    <div className="project-state__section-heading">
      <h2>{title}</h2>
      <span>{count}</span>
    </div>
  );
}

function StageCreateForm({
  onCreate,
  busy,
  nextPosition,
}: {
  onCreate: (data: StageCreate, done: () => void) => void;
  busy: boolean;
  nextPosition: number;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [startDate, setStartDate] = useState('');
  const [dueDate, setDueDate] = useState('');
  return (
    <form
      className="project-state__editor"
      onSubmit={(event) => {
        event.preventDefault();
        onCreate(
          {
            name: name.trim(),
            description: description.trim(),
            position: nextPosition,
            start_date: startDate || null,
            due_date: dueDate || null,
          },
          () => {
            setName('');
            setDescription('');
            setStartDate('');
            setDueDate('');
          },
        );
      }}
    >
      <label className="form-field">
        Stage name
        <input
          required
          maxLength={200}
          value={name}
          onChange={(event) => setName(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Description
        <textarea
          rows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Start date
        <input
          type="date"
          value={startDate}
          onChange={(event) => setStartDate(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Due date
        <input
          type="date"
          value={dueDate}
          onChange={(event) => setDueDate(event.currentTarget.value)}
        />
      </label>
      <button className="button button--primary" disabled={busy} type="submit">
        {busy ? 'Saving…' : 'Create stage'}
      </button>
    </form>
  );
}

function RequirementCreateForm({
  onCreate,
  busy,
}: {
  onCreate: (data: RequirementCreate, done: () => void) => void;
  busy: boolean;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  return (
    <form
      className="project-state__editor"
      onSubmit={(event) => {
        event.preventDefault();
        onCreate({ title: title.trim(), description: description.trim() }, () => {
          setTitle('');
          setDescription('');
        });
      }}
    >
      <label className="form-field">
        Requirement
        <input
          required
          maxLength={255}
          value={title}
          onChange={(event) => setTitle(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Description
        <textarea
          rows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
      </label>
      <button className="button button--primary" disabled={busy} type="submit">
        {busy ? 'Saving…' : 'Create requirement'}
      </button>
    </form>
  );
}

function TaskCreateForm({
  onCreate,
  busy,
  stages,
  members,
}: {
  onCreate: (data: TaskCreate, done: () => void) => void;
  busy: boolean;
  stages: ProjectStage[];
  members: Array<{ user_id: string; role: string; first_name: string; last_name: string }>;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [stageId, setStageId] = useState('');
  const [assigneeId, setAssigneeId] = useState('');
  const [dueDate, setDueDate] = useState('');
  return (
    <form
      className="project-state__editor"
      onSubmit={(event) => {
        event.preventDefault();
        onCreate(
          {
            title: title.trim(),
            description: description.trim(),
            stage_id: stageId || null,
            assignee_id: assigneeId || null,
            due_date: dueDate || null,
          },
          () => {
            setTitle('');
            setDescription('');
            setStageId('');
            setAssigneeId('');
            setDueDate('');
          },
        );
      }}
    >
      <label className="form-field">
        Task
        <input
          required
          maxLength={255}
          value={title}
          onChange={(event) => setTitle(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Description
        <textarea
          rows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Stage
        <select value={stageId} onChange={(event) => setStageId(event.currentTarget.value)}>
          <option value="">No stage</option>
          {stages.map((stage) => (
            <option key={stage.id} value={stage.id}>
              {stage.name}
            </option>
          ))}
        </select>
      </label>
      <label className="form-field">
        Assignee
        <select value={assigneeId} onChange={(event) => setAssigneeId(event.currentTarget.value)}>
          <option value="">Unassigned</option>
          {members.map((member) => (
            <option key={member.user_id} value={member.user_id}>
              {[member.first_name, member.last_name].filter(Boolean).join(' ') || member.role}
            </option>
          ))}
        </select>
      </label>
      <label className="form-field">
        Due date
        <input
          type="date"
          value={dueDate}
          onChange={(event) => setDueDate(event.currentTarget.value)}
        />
      </label>
      <button className="button button--primary" disabled={busy} type="submit">
        {busy ? 'Saving…' : 'Create task'}
      </button>
    </form>
  );
}

function OpenQuestionCreateForm({
  onCreate,
  busy,
}: {
  onCreate: (data: OpenQuestionCreate, done: () => void) => void;
  busy: boolean;
}) {
  const [question, setQuestion] = useState('');
  return (
    <form
      className="project-state__editor"
      onSubmit={(event) => {
        event.preventDefault();
        onCreate({ question: question.trim(), answer: '' }, () => setQuestion(''));
      }}
    >
      <label className="form-field">
        Question
        <textarea
          required
          rows={2}
          value={question}
          onChange={(event) => setQuestion(event.currentTarget.value)}
        />
      </label>
      <button className="button button--primary" disabled={busy} type="submit">
        {busy ? 'Saving…' : 'Create question'}
      </button>
    </form>
  );
}

function ConflictCreateForm({
  options,
  onCreate,
  busy,
}: {
  options: EvidenceOption[];
  onCreate: (data: ProjectConflictCreate, done: () => void) => void;
  busy: boolean;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [selected, setSelected] = useState<string[]>([]);

  function toggle(sourceId: string) {
    setSelected((current) =>
      current.includes(sourceId) ? current.filter((id) => id !== sourceId) : [...current, sourceId],
    );
  }

  return (
    <form
      className="project-state__editor"
      onSubmit={(event) => {
        event.preventDefault();
        onCreate(
          {
            title: title.trim(),
            description: description.trim(),
            evidence_refs: selected.map((source_id) => ({
              source_type: 'questionnaire_answer',
              source_id,
            })),
          },
          () => {
            setTitle('');
            setDescription('');
            setSelected([]);
          },
        );
      }}
    >
      <label className="form-field">
        Conflict title
        <input
          required
          maxLength={255}
          value={title}
          onChange={(event) => setTitle(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Description
        <textarea
          rows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
      </label>
      <fieldset className="project-state__evidence-picker">
        <legend>Choose at least two submitted questionnaire answers</legend>
        {options.length === 0 ? (
          <p>No submitted answers are available as evidence yet.</p>
        ) : (
          options.map((option) => (
            <label key={option.source_id}>
              <input
                checked={selected.includes(option.source_id)}
                onChange={() => toggle(option.source_id)}
                type="checkbox"
              />
              <span>
                <strong>{option.question_key.replaceAll('_', ' ')}</strong> —{' '}
                {JSON.stringify(option.value)}
              </span>
            </label>
          ))
        )}
      </fieldset>
      <button
        className="button button--primary"
        disabled={busy || selected.length < 2}
        type="submit"
      >
        {busy ? 'Saving…' : 'Create conflict'}
      </button>
      {selected.length < 2 && (
        <p className="project-state__hint">Select two answers to create a conflict record.</p>
      )}
    </form>
  );
}

export function ProjectStatePage() {
  const user = useOutletContext<User>();
  const { projectId = '' } = useParams();
  const projectQuery = useProject(projectId);
  const membersQuery = useProjectMembers(projectId);
  const aggregateQuery = useProjectStateAggregate(projectId);
  const stagesQuery = useProjectStateCollection(projectId, 'stages');
  const requirementsQuery = useProjectStateCollection(projectId, 'requirements');
  const tasksQuery = useProjectStateCollection(projectId, 'tasks');
  const questionsQuery = useProjectStateCollection(projectId, 'open-questions');
  const conflictsQuery = useProjectStateCollection(projectId, 'conflicts');
  const member = membersQuery.data?.find((candidate) => candidate.user_id === user.id);
  const isExecutor = member?.role === 'executor';
  const evidenceOptionsQuery = useProjectStateEvidenceOptions(projectId, isExecutor);
  const createStage = useCreateProjectStateRecord(projectId, 'stages');
  const createRequirement = useCreateProjectStateRecord(projectId, 'requirements');
  const createTask = useCreateProjectStateRecord(projectId, 'tasks');
  const createQuestion = useCreateProjectStateRecord(projectId, 'open-questions');
  const createConflict = useCreateProjectStateRecord(projectId, 'conflicts');
  const updateStage = useUpdateProjectStateRecord(projectId, 'stage');
  const updateRequirement = useUpdateProjectStateRecord(projectId, 'requirement');
  const updateTask = useUpdateProjectStateRecord(projectId, 'task');
  const updateQuestion = useUpdateProjectStateRecord(projectId, 'open-question');
  const updateConflict = useUpdateProjectStateRecord(projectId, 'conflict');
  const stateQueries = [
    aggregateQuery,
    stagesQuery,
    requirementsQuery,
    tasksQuery,
    questionsQuery,
    conflictsQuery,
  ];

  async function retry() {
    await Promise.all([
      projectQuery.refetch(),
      membersQuery.refetch(),
      ...stateQueries.map((query) => query.refetch()),
      ...(isExecutor ? [evidenceOptionsQuery.refetch()] : []),
    ]);
  }

  if (projectQuery.isError || membersQuery.isError || stateQueries.some((query) => query.isError)) {
    const error =
      projectQuery.error ??
      membersQuery.error ??
      stateQueries.find((query) => query.isError)?.error;
    return (
      <main className="workspace-page workspace-page--narrow">
        <section
          className="state-message state-message--error"
          aria-labelledby="project-state-error-title"
        >
          <h1 id="project-state-error-title">We couldn’t load Project State</h1>
          <p>
            {error instanceof ApiError && error.status === 404
              ? 'This project is unavailable to your account.'
              : error?.message || 'Check your connection and try again.'}
          </p>
          <button className="button button--secondary" onClick={() => void retry()} type="button">
            Try again
          </button>
        </section>
      </main>
    );
  }

  if (
    projectQuery.isPending ||
    membersQuery.isPending ||
    stateQueries.some((query) => query.isPending) ||
    !projectQuery.data ||
    !membersQuery.data ||
    !aggregateQuery.data ||
    !stagesQuery.data ||
    !requirementsQuery.data ||
    !tasksQuery.data ||
    !questionsQuery.data ||
    !conflictsQuery.data
  ) {
    return (
      <main className="workspace-page">
        <p className="state-message" role="status">
          Loading Project State…
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

  const project = projectQuery.data;
  const canEdit = isExecutor && (project.status === 'draft' || project.status === 'active');
  const stages = stagesQuery.data.results;
  const requirements = requirementsQuery.data.results;
  const tasks = tasksQuery.data.results;
  const questions = questionsQuery.data.results;
  const conflicts = conflictsQuery.data.results;
  const activeMembers = membersQuery.data;
  const mutationErrors = [
    createStage.error,
    createRequirement.error,
    createTask.error,
    createQuestion.error,
    createConflict.error,
    updateStage.error,
    updateRequirement.error,
    updateTask.error,
    updateQuestion.error,
    updateConflict.error,
  ].filter((error): error is Error => error !== null);

  return (
    <main className="workspace-page project-state-page">
      <Link className="back-link" to={`/app/projects/${project.id}`}>
        Back to project
      </Link>
      <header className="project-state__header">
        <div>
          <p className="eyebrow">Shared project plan</p>
          <h1>Project State</h1>
          <p>Stages, requirements, tasks, open questions and recorded conflicts.</p>
        </div>
        <span
          className={`project-state__project-status project-state__project-status--${project.status}`}
        >
          {statusText(project.status)}
        </span>
      </header>
      {!canEdit && project.status !== 'draft' && project.status !== 'active' && (
        <p className="project-state__readonly-note">
          This project is read-only while it is {statusText(project.status)}.
        </p>
      )}
      {mutationErrors.length > 0 && (
        <p className="state-message state-message--error" role="alert">
          {mutationErrors[0].message ||
            'Project State could not be saved. Your edits are still here.'}
        </p>
      )}
      <fieldset className="project-state__summary" aria-label="Project State record counts">
        {Object.entries(aggregateQuery.data.counts).map(([label, count]) => (
          <div key={label}>
            <strong>{count}</strong>
            <span>{label.replaceAll('_', ' ')}</span>
          </div>
        ))}
      </fieldset>

      <section className="project-state__section" aria-labelledby="project-state-stages">
        <SectionHeader title="Stages" count={aggregateQuery.data.counts.stages} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Add stage</summary>
            <StageCreateForm
              busy={createStage.isPending}
              nextPosition={stages.length}
              onCreate={(data, done) => createStage.mutate(data, { onSuccess: done })}
            />
          </details>
        )}
        {stages.length === 0 ? (
          <EmptyMessage canEdit={canEdit} entity="stages" />
        ) : (
          <div className="project-state__records">
            {stages.map((stage) => (
              <StageCard
                key={stage.id}
                canEdit={canEdit}
                save={(id, changes, done) =>
                  updateStage.mutate({ recordId: id, changes }, { onSuccess: done })
                }
                stage={stage}
              />
            ))}
          </div>
        )}
      </section>

      <section className="project-state__section" aria-labelledby="project-state-requirements">
        <SectionHeader title="Requirements" count={aggregateQuery.data.counts.requirements} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Add requirement</summary>
            <RequirementCreateForm
              busy={createRequirement.isPending}
              onCreate={(data, done) => createRequirement.mutate(data, { onSuccess: done })}
            />
          </details>
        )}
        {requirements.length === 0 ? (
          <EmptyMessage canEdit={canEdit} entity="requirements" />
        ) : (
          <div className="project-state__records">
            {requirements.map((item) => (
              <RequirementCard
                key={item.id}
                canEdit={canEdit}
                requirement={item}
                save={(id, changes, done) =>
                  updateRequirement.mutate({ recordId: id, changes }, { onSuccess: done })
                }
              />
            ))}
          </div>
        )}
      </section>

      <section className="project-state__section" aria-labelledby="project-state-tasks">
        <SectionHeader title="Tasks" count={aggregateQuery.data.counts.tasks} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Add task</summary>
            <TaskCreateForm
              busy={createTask.isPending}
              members={activeMembers}
              onCreate={(data, done) => createTask.mutate(data, { onSuccess: done })}
              stages={stages}
            />
          </details>
        )}
        {tasks.length === 0 ? (
          <EmptyMessage canEdit={canEdit} entity="tasks" />
        ) : (
          <div className="project-state__records">
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                canEdit={canEdit}
                members={activeMembers}
                save={(id, changes, done) =>
                  updateTask.mutate({ recordId: id, changes }, { onSuccess: done })
                }
                stages={stages}
                task={task}
              />
            ))}
          </div>
        )}
      </section>

      <section className="project-state__section" aria-labelledby="project-state-questions">
        <SectionHeader title="Open questions" count={aggregateQuery.data.counts.open_questions} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Add question</summary>
            <OpenQuestionCreateForm
              busy={createQuestion.isPending}
              onCreate={(data, done) => createQuestion.mutate(data, { onSuccess: done })}
            />
          </details>
        )}
        {questions.length === 0 ? (
          <EmptyMessage canEdit={canEdit} entity="open questions" />
        ) : (
          <div className="project-state__records">
            {questions.map((item) => (
              <OpenQuestionCard
                key={item.id}
                canEdit={canEdit}
                item={item}
                save={(id, changes, done) =>
                  updateQuestion.mutate({ recordId: id, changes }, { onSuccess: done })
                }
              />
            ))}
          </div>
        )}
      </section>

      <section className="project-state__section" aria-labelledby="project-state-conflicts">
        <SectionHeader title="Conflicts" count={aggregateQuery.data.counts.conflicts} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Record a conflict</summary>
            {evidenceOptionsQuery.isError ? (
              <div className="state-message state-message--error">
                <p>{evidenceOptionsQuery.error.message}</p>
                <button
                  className="button button--secondary"
                  onClick={() => void evidenceOptionsQuery.refetch()}
                  type="button"
                >
                  Retry evidence
                </button>
              </div>
            ) : evidenceOptionsQuery.isPending ? (
              <p role="status">Loading evidence…</p>
            ) : (
              <ConflictCreateForm
                busy={createConflict.isPending}
                onCreate={(data, done) => createConflict.mutate(data, { onSuccess: done })}
                options={evidenceOptionsQuery.data?.results ?? []}
              />
            )}
          </details>
        )}
        {conflicts.length === 0 ? (
          <EmptyMessage canEdit={canEdit} entity="conflicts" />
        ) : (
          <div className="project-state__records">
            {conflicts.map((conflict) => (
              <ProjectConflictCard
                key={conflict.id}
                canEdit={canEdit}
                conflict={conflict}
                save={(id, changes, done) =>
                  updateConflict.mutate({ recordId: id, changes }, { onSuccess: done })
                }
              />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
