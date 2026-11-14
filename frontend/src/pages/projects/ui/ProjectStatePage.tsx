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

function nextStatuses(graph: Record<string, string[]>, current: string): string[] {
  return graph[current] ?? [];
}

function evidenceQuestionLabel(metadata: unknown): string {
  if (metadata && typeof metadata === 'object' && 'question_key' in metadata) {
    const questionKey = (metadata as { question_key?: unknown }).question_key;
    if (typeof questionKey === 'string') return questionKey.replaceAll('_', ' ');
  }
  return 'Ответ анкеты';
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
    return <p className="project-state__terminal">Статус: {statusText(current)}</p>;
  }
  return (
    <label className="form-field" htmlFor={label}>
      Статус
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
        {stage.start_date ? `Начало: ${stage.start_date}` : 'Дата начала не указана'}
        {' · '}
        {stage.due_date ? `Срок: ${stage.due_date}` : 'Срок не указан'}
      </p>
      {canEdit && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          Изменить этап
        </button>
      )}
      {canEdit && editing && (
        <form className="project-state__editor" onSubmit={submit}>
          <label className="form-field">
            Название этапа
            <input
              required
              maxLength={200}
              value={name}
              onChange={(event) => setName(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Описание
            <textarea
              rows={2}
              value={description}
              onChange={(event) => setDescription(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Позиция
            <input
              min={0}
              type="number"
              value={position}
              onChange={(event) => setPosition(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Дата начала
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Срок
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
              Сохранить этап
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Отмена
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
          Подтверждено {new Date(requirement.confirmed_at).toLocaleDateString()}
        </p>
      )}
      {canEdit && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          Изменить требование
        </button>
      )}
      {canEdit && editing && (
        <form className="project-state__editor" onSubmit={submit}>
          <label className="form-field">
            Требование
            <input
              required
              maxLength={255}
              value={title}
              onChange={(event) => setTitle(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Описание
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
              Сохранить требование
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Отмена
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
      (assignedMember.role === 'executor' ? 'Исполнитель' : 'Заказчик')
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
        {task.due_date ? `Срок: ${task.due_date}` : 'Срок не указан'}
        {assignedName ? ` · Исполнитель: ${assignedName}` : ''}
      </p>
      {task.stage_id && (
        <p className="project-state__dates">
          Этап: {stages.find((stage) => stage.id === task.stage_id)?.name ?? 'Недоступно'}
        </p>
      )}
      {canEdit && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          Изменить задачу
        </button>
      )}
      {canEdit && editing && (
        <form className="project-state__editor" onSubmit={submit}>
          <label className="form-field">
            Задача
            <input
              required
              maxLength={255}
              value={title}
              onChange={(event) => setTitle(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Описание
            <textarea
              rows={2}
              value={description}
              onChange={(event) => setDescription(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Этап
            <select value={stageId} onChange={(event) => setStageId(event.currentTarget.value)}>
              <option value="">Без этапа</option>
              {stages.map((stage) => (
                <option key={stage.id} value={stage.id}>
                  {stage.name}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            Исполнитель
            <select
              value={assigneeId}
              onChange={(event) => setAssigneeId(event.currentTarget.value)}
            >
              <option value="">Не назначено</option>
              {members.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {[member.first_name, member.last_name].filter(Boolean).join(' ') ||
                    (member.role === 'executor' ? 'Исполнитель' : 'Заказчик')}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            Срок
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
              Сохранить задачу
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Отмена
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
          Закрыто {new Date(item.resolved_at).toLocaleDateString()}
        </p>
      )}
      {canEdit && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          Изменить вопрос
        </button>
      )}
      {canEdit && editing && (
        <form className="project-state__editor" onSubmit={submit}>
          <label className="form-field">
            Вопрос
            <textarea
              required
              rows={2}
              value={question}
              onChange={(event) => setQuestion(event.currentTarget.value)}
            />
          </label>
          <label className="form-field">
            Ответ
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
              Сохранить вопрос
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Отмена
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
          <strong>Решение:</strong> {conflict.resolution}
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
          Принято решение {new Date(conflict.resolved_at).toLocaleDateString()}
        </p>
      )}
      {canEdit && conflict.status === 'unresolved' && !editing && (
        <button className="button button--quiet" type="button" onClick={() => setEditing(true)}>
          {options.length > 0 ? 'Разрешить противоречие' : 'Изменить противоречие'}
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
            Решение
            <textarea
              required={nextStatus === 'resolved'}
              rows={3}
              value={resolution}
              onChange={(event) => setResolution(event.currentTarget.value)}
            />
          </label>
          <div className="form-actions">
            <button className="button button--primary" type="submit">
              Сохранить противоречие
            </button>
            <button
              className="button button--secondary"
              onClick={() => setEditing(false)}
              type="button"
            >
              Отмена
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
        ? `Добавьте ${entity} в общий план проекта.`
        : `Исполнитель ещё не добавил ${entity}.`}
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
        Название этапа
        <input
          required
          maxLength={200}
          value={name}
          onChange={(event) => setName(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Описание
        <textarea
          rows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Дата начала
        <input
          type="date"
          value={startDate}
          onChange={(event) => setStartDate(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Срок
        <input
          type="date"
          value={dueDate}
          onChange={(event) => setDueDate(event.currentTarget.value)}
        />
      </label>
      <button className="button button--primary" disabled={busy} type="submit">
        {busy ? 'Saving…' : 'Создать этап'}
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
        Требование
        <input
          required
          maxLength={255}
          value={title}
          onChange={(event) => setTitle(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Описание
        <textarea
          rows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
      </label>
      <button className="button button--primary" disabled={busy} type="submit">
        {busy ? 'Saving…' : 'Создать требование'}
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
        Задача
        <input
          required
          maxLength={255}
          value={title}
          onChange={(event) => setTitle(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Описание
        <textarea
          rows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Этап
        <select value={stageId} onChange={(event) => setStageId(event.currentTarget.value)}>
          <option value="">Без этапа</option>
          {stages.map((stage) => (
            <option key={stage.id} value={stage.id}>
              {stage.name}
            </option>
          ))}
        </select>
      </label>
      <label className="form-field">
        Исполнитель
        <select value={assigneeId} onChange={(event) => setAssigneeId(event.currentTarget.value)}>
          <option value="">Не назначено</option>
          {members.map((member) => (
            <option key={member.user_id} value={member.user_id}>
              {[member.first_name, member.last_name].filter(Boolean).join(' ') ||
                (member.role === 'executor' ? 'Исполнитель' : 'Заказчик')}
            </option>
          ))}
        </select>
      </label>
      <label className="form-field">
        Срок
        <input
          type="date"
          value={dueDate}
          onChange={(event) => setDueDate(event.currentTarget.value)}
        />
      </label>
      <button className="button button--primary" disabled={busy} type="submit">
        {busy ? 'Saving…' : 'Создать задачу'}
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
        Вопрос
        <textarea
          required
          rows={2}
          value={question}
          onChange={(event) => setQuestion(event.currentTarget.value)}
        />
      </label>
      <button className="button button--primary" disabled={busy} type="submit">
        {busy ? 'Saving…' : 'Создать вопрос'}
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
        Название противоречия
        <input
          required
          maxLength={255}
          value={title}
          onChange={(event) => setTitle(event.currentTarget.value)}
        />
      </label>
      <label className="form-field">
        Описание
        <textarea
          rows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
      </label>
      <fieldset className="project-state__evidence-picker">
        <legend>Выберите не менее двух отправленных ответов анкеты</legend>
        {options.length === 0 ? (
          <p>Отправленных ответов для подтверждения пока нет.</p>
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
        {busy ? 'Saving…' : 'Создать противоречие'}
      </button>
      {selected.length < 2 && (
        <p className="project-state__hint">
          Выберите два ответа, чтобы зафиксировать противоречие.
        </p>
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
          <h1 id="project-state-error-title">Не удалось загрузить состояние проекта</h1>
          <p>
            {error instanceof ApiError && error.status === 404
              ? 'Проект недоступен вашему аккаунту.'
              : error?.message || 'Проверьте подключение и попробуйте снова.'}
          </p>
          <button className="button button--secondary" onClick={() => void retry()} type="button">
            Попробовать снова
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
          Загрузка состояния проекта…
        </p>
      </main>
    );
  }

  if (!member) {
    return (
      <main className="workspace-page workspace-page--narrow">
        <p className="state-message state-message--error" role="alert">
          Не удалось подтвердить ваше участие в проекте.
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
        К проекту
      </Link>
      <header className="project-state__header">
        <div>
          <p className="eyebrow">Общий план проекта</p>
          <h1>Состояние проекта</h1>
          <p>Этапы, требования, задачи, открытые вопросы и зафиксированные противоречия.</p>
        </div>
        <span
          className={`project-state__project-status project-state__project-status--${project.status}`}
        >
          {statusText(project.status)}
        </span>
      </header>
      {!canEdit && project.status !== 'draft' && project.status !== 'active' && (
        <p className="project-state__readonly-note">
          Проект доступен только для чтения. Статус: {statusText(project.status)}.
        </p>
      )}
      {mutationErrors.length > 0 && (
        <p className="state-message state-message--error" role="alert">
          {mutationErrors[0].message ||
            'Не удалось сохранить состояние проекта. Ваши изменения остались на странице.'}
        </p>
      )}
      <fieldset
        className="project-state__summary"
        aria-label="Количество записей состояния проекта"
      >
        {Object.entries(aggregateQuery.data.counts).map(([label, count]) => (
          <div key={label}>
            <strong>{count}</strong>
            <span>{label.replaceAll('_', ' ')}</span>
          </div>
        ))}
      </fieldset>

      <section className="project-state__section" aria-labelledby="project-state-stages">
        <SectionHeader title="Этапы" count={aggregateQuery.data.counts.stages} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Добавить этап</summary>
            <StageCreateForm
              busy={createStage.isPending}
              nextPosition={stages.length}
              onCreate={(data, done) => createStage.mutate(data, { onSuccess: done })}
            />
          </details>
        )}
        {stages.length === 0 ? (
          <EmptyMessage canEdit={canEdit} entity="этапы" />
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
        <SectionHeader title="Требования" count={aggregateQuery.data.counts.requirements} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Добавить требование</summary>
            <RequirementCreateForm
              busy={createRequirement.isPending}
              onCreate={(data, done) => createRequirement.mutate(data, { onSuccess: done })}
            />
          </details>
        )}
        {requirements.length === 0 ? (
          <EmptyMessage canEdit={canEdit} entity="требования" />
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
        <SectionHeader title="Задачи" count={aggregateQuery.data.counts.tasks} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Добавить задачу</summary>
            <TaskCreateForm
              busy={createTask.isPending}
              members={activeMembers}
              onCreate={(data, done) => createTask.mutate(data, { onSuccess: done })}
              stages={stages}
            />
          </details>
        )}
        {tasks.length === 0 ? (
          <EmptyMessage canEdit={canEdit} entity="задачи" />
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
        <SectionHeader title="Открытые вопросы" count={aggregateQuery.data.counts.open_questions} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Добавить вопрос</summary>
            <OpenQuestionCreateForm
              busy={createQuestion.isPending}
              onCreate={(data, done) => createQuestion.mutate(data, { onSuccess: done })}
            />
          </details>
        )}
        {questions.length === 0 ? (
          <EmptyMessage canEdit={canEdit} entity="открытые вопросы" />
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
        <SectionHeader title="Противоречия" count={aggregateQuery.data.counts.conflicts} />
        {canEdit && (
          <details className="project-state__create">
            <summary>Зафиксировать противоречие</summary>
            {evidenceOptionsQuery.isError ? (
              <div className="state-message state-message--error">
                <p>{evidenceOptionsQuery.error.message}</p>
                <button
                  className="button button--secondary"
                  onClick={() => void evidenceOptionsQuery.refetch()}
                  type="button"
                >
                  Повторить загрузку источников
                </button>
              </div>
            ) : evidenceOptionsQuery.isPending ? (
              <p role="status">Загрузка источников…</p>
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
          <EmptyMessage canEdit={canEdit} entity="противоречия" />
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
