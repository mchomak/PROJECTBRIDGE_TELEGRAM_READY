import { useState } from 'react';
import { Link } from 'react-router';
import {
  projectStatusLabels,
  projectTypeOptions,
  useProjectList,
  type Project,
} from '../../../entities/project';
import { ApiError } from '../../../shared/api';

function projectTypeLabel(project: Project): string {
  return (
    projectTypeOptions.find((option) => option.value === project.project_type)?.label ?? 'Other'
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function ProjectRows({ projects }: { projects: Project[] }) {
  return (
    <ul className="project-list" aria-label="Projects">
      {projects.map((project) => (
        <li className="project-row" key={project.id}>
          <Link className="project-row__main" to={`/app/projects/${project.id}`}>
            <span className="project-row__name">{project.name}</span>
            <span className="project-row__meta">
              {projectTypeLabel(project)} · Updated {formatDate(project.updated_at)}
            </span>
          </Link>
          <span className={`status-badge status-badge--${project.status}`}>
            {projectStatusLabels[project.status]}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function ProjectListPage({ archived = false }: { archived?: boolean }) {
  const [page, setPage] = useState(1);
  const projects = useProjectList(archived, page);
  const title = archived ? 'Archived projects' : 'Projects';

  return (
    <main className="workspace-page">
      <div className="page-heading">
        <div>
          <h1>{title}</h1>
          <p className="page-heading__description">
            {archived
              ? 'Archived projects remain available to their active participants.'
              : 'Plan, manage, and keep your project details in one place.'}
          </p>
        </div>
        {archived ? (
          <Link className="button button--secondary" to="/app/projects">
            Back to projects
          </Link>
        ) : (
          <Link className="button button--primary" to="/app/projects/new">
            Create project
          </Link>
        )}
      </div>

      {projects.isPending && (
        <p className="state-message" role="status">
          Loading projects…
        </p>
      )}

      {projects.isError && (
        <section
          className="state-message state-message--error"
          aria-labelledby="project-list-error"
        >
          <h2 id="project-list-error">We couldn’t load these projects</h2>
          <p>
            {projects.error instanceof ApiError
              ? projects.error.message
              : 'Check your connection and try again.'}
          </p>
          <button
            className="button button--secondary"
            onClick={() => void projects.refetch()}
            type="button"
          >
            Try again
          </button>
        </section>
      )}

      {projects.data && projects.data.results.length === 0 && (
        <section className="empty-state" aria-labelledby="project-list-empty">
          <h2 id="project-list-empty">
            {archived ? 'No archived projects' : 'Your workspace is ready'}
          </h2>
          <p>
            {archived
              ? 'Projects will appear here when an executor archives them.'
              : 'Create a project to capture its goals, scope, timeline, and budget.'}
          </p>
          {!archived && (
            <Link className="button button--primary" to="/app/projects/new">
              Create your first project
            </Link>
          )}
        </section>
      )}

      {projects.data && projects.data.results.length > 0 && (
        <>
          <ProjectRows projects={projects.data.results} />
          <nav className="pagination" aria-label="Project list pages">
            <span>
              {projects.data.count} {projects.data.count === 1 ? 'project' : 'projects'}
            </span>
            <div className="pagination__actions">
              <button
                className="button button--secondary"
                disabled={!projects.data.previous || page === 1 || projects.isFetching}
                onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                type="button"
              >
                Previous
              </button>
              <span aria-live="polite">Page {page}</span>
              <button
                className="button button--secondary"
                disabled={!projects.data.next || projects.isFetching}
                onClick={() => setPage((currentPage) => currentPage + 1)}
                type="button"
              >
                Next
              </button>
            </div>
          </nav>
        </>
      )}
    </main>
  );
}
