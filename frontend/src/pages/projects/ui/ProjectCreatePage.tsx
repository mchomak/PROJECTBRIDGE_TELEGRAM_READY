import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { projectTypeOptions, type ProjectType } from '../../../entities/project';
import { useCreateProject } from '../../../features/projects';
import { ApiError, getApiFieldErrors } from '../../../shared/api';

export function ProjectCreatePage() {
  const navigate = useNavigate();
  const createProject = useCreateProject();
  const [name, setName] = useState('');
  const [projectType, setProjectType] = useState<ProjectType | ''>('');
  const [description, setDescription] = useState('');
  const [validationErrors, setValidationErrors] = useState<Record<string, string[]>>({});
  const fieldErrors = { ...getApiFieldErrors(createProject.error), ...validationErrors };

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors: Record<string, string[]> = {};
    if (!name.trim()) nextErrors.name = ['Введите название проекта.'];
    if (name.trim().length > 200) nextErrors.name = ['Не более 200 символов.'];
    if (!projectType) nextErrors.project_type = ['Выберите тип проекта.'];
    setValidationErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    createProject.mutate(
      {
        name: name.trim(),
        project_type: projectType as ProjectType,
        description: description.trim() || null,
      },
      { onSuccess: (project) => navigate(`/app/projects/${project.id}`) },
    );
  }

  function clearValidation(field: string) {
    setValidationErrors((current) => ({ ...current, [field]: [] }));
  }

  return (
    <main className="workspace-page workspace-page--narrow">
      <Link className="back-link" to="/app/projects">
        ← К проектам
      </Link>
      <div className="page-heading page-heading--compact">
        <div>
          <h1>Создать проект</h1>
          <p className="page-heading__description">
            Начните с основ. Подробности можно добавить на странице проекта.
          </p>
        </div>
      </div>

      <form className="form-panel" onSubmit={submit} noValidate>
        <div className="form-field">
          <label htmlFor="project-name">Название проекта</label>
          <input
            autoComplete="off"
            id="project-name"
            maxLength={200}
            name="name"
            onChange={(event) => {
              setName(event.currentTarget.value);
              clearValidation('name');
            }}
            required
            value={name}
            aria-invalid={Boolean(fieldErrors.name?.length)}
            aria-describedby={fieldErrors.name?.length ? 'project-name-error' : 'project-name-help'}
          />
          <p className="field-help" id="project-name-help">
            До 200 символов.
          </p>
          {fieldErrors.name?.map((message) => (
            <p className="field-error" id="project-name-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>

        <div className="form-field">
          <label htmlFor="project-type">Тип проекта</label>
          <select
            id="project-type"
            name="project_type"
            onChange={(event) => {
              setProjectType(event.currentTarget.value as ProjectType | '');
              clearValidation('project_type');
            }}
            required
            value={projectType}
            aria-invalid={Boolean(fieldErrors.project_type?.length)}
            aria-describedby={fieldErrors.project_type?.length ? 'project-type-error' : undefined}
          >
            <option value="">Выберите тип проекта</option>
            {projectTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {fieldErrors.project_type?.map((message) => (
            <p className="field-error" id="project-type-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>

        <div className="form-field">
          <label htmlFor="project-description">
            Описание <span>(необязательно)</span>
          </label>
          <textarea
            id="project-description"
            name="description"
            onChange={(event) => setDescription(event.currentTarget.value)}
            rows={5}
            value={description}
          />
          {fieldErrors.description?.map((message) => (
            <p className="field-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>

        {createProject.error &&
          Object.keys(getApiFieldErrors(createProject.error)).length === 0 && (
            <p className="form-error" role="alert">
              {createProject.error instanceof ApiError
                ? createProject.error.message
                : 'Не удалось создать проект. Введённые данные сохранены на странице; попробуйте снова.'}
            </p>
          )}

        <div className="form-actions">
          <Link className="button button--secondary" to="/app/projects">
            Отмена
          </Link>
          <button
            className="button button--primary"
            disabled={createProject.isPending}
            type="submit"
          >
            {createProject.isPending ? 'Создание…' : 'Создать проект'}
          </button>
        </div>
      </form>
    </main>
  );
}
