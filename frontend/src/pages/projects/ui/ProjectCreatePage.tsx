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
    if (!name.trim()) nextErrors.name = ['Enter a project name.'];
    if (name.trim().length > 200) nextErrors.name = ['Use 200 characters or fewer.'];
    if (!projectType) nextErrors.project_type = ['Choose a project type.'];
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
        ← Back to projects
      </Link>
      <div className="page-heading page-heading--compact">
        <div>
          <h1>Create a project</h1>
          <p className="page-heading__description">
            Start with the basics. You can add the full project brief on its overview page.
          </p>
        </div>
      </div>

      <form className="form-panel" onSubmit={submit} noValidate>
        <div className="form-field">
          <label htmlFor="project-name">Project name</label>
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
            Up to 200 characters.
          </p>
          {fieldErrors.name?.map((message) => (
            <p className="field-error" id="project-name-error" key={message} role="alert">
              {message}
            </p>
          ))}
        </div>

        <div className="form-field">
          <label htmlFor="project-type">Project type</label>
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
            <option value="">Select a project type</option>
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
            Description <span>(optional)</span>
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
                : 'We couldn’t create the project. Your entries are still here; try again.'}
            </p>
          )}

        <div className="form-actions">
          <Link className="button button--secondary" to="/app/projects">
            Cancel
          </Link>
          <button
            className="button button--primary"
            disabled={createProject.isPending}
            type="submit"
          >
            {createProject.isPending ? 'Creating…' : 'Create project'}
          </button>
        </div>
      </form>
    </main>
  );
}
