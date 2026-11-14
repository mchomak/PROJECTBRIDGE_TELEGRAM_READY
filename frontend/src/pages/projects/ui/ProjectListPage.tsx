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
    projectTypeOptions.find((option) => option.value === project.project_type)?.label ?? 'Другое'
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

function projectCountLabel(count: number): string {
  const form = new Intl.PluralRules('ru').select(count);
  return form === 'one' ? 'проект' : form === 'few' ? 'проекта' : 'проектов';
}

function ProjectRows({ projects }: { projects: Project[] }) {
  return (
    <ul className="project-list" aria-label="Проекты">
      {projects.map((project) => (
        <li className="project-row" key={project.id}>
          <Link className="project-row__main" to={`/app/projects/${project.id}`}>
            <span className="project-row__name">{project.name}</span>
            <span className="project-row__meta">
              {projectTypeLabel(project)} · Обновлён {formatDate(project.updated_at)}
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
  const title = archived ? 'Архивные проекты' : 'Проекты';

  return (
    <main className="workspace-page">
      <div className="page-heading">
        <div>
          <h1>{title}</h1>
          <p className="page-heading__description">
            {archived
              ? 'Архивные проекты доступны их активным участникам.'
              : 'Планируйте проект и храните все его данные в одном месте.'}
          </p>
        </div>
        {archived ? (
          <Link className="button button--secondary" to="/app/projects">
            К проектам
          </Link>
        ) : (
          <Link className="button button--primary" to="/app/projects/new">
            Создать проект
          </Link>
        )}
      </div>

      {projects.isPending && (
        <p className="state-message" role="status">
          Загрузка проектов…
        </p>
      )}

      {projects.isError && (
        <section
          className="state-message state-message--error"
          aria-labelledby="project-list-error"
        >
          <h2 id="project-list-error">Не удалось загрузить проекты</h2>
          <p>
            {projects.error instanceof ApiError
              ? projects.error.message
              : 'Проверьте подключение и попробуйте снова.'}
          </p>
          <button
            className="button button--secondary"
            onClick={() => void projects.refetch()}
            type="button"
          >
            Попробовать снова
          </button>
        </section>
      )}

      {projects.data && projects.data.results.length === 0 && (
        <section className="empty-state" aria-labelledby="project-list-empty">
          <h2 id="project-list-empty">
            {archived ? 'Нет архивных проектов' : 'Рабочее пространство готово'}
          </h2>
          <p>
            {archived
              ? 'Здесь появятся проекты, которые исполнитель перенесёт в архив.'
              : 'Создайте проект, чтобы зафиксировать цели, объём работ, сроки и бюджет.'}
          </p>
          {!archived && (
            <Link className="button button--primary" to="/app/projects/new">
              Создать первый проект
            </Link>
          )}
        </section>
      )}

      {projects.data && projects.data.results.length > 0 && (
        <>
          <ProjectRows projects={projects.data.results} />
          <nav className="pagination" aria-label="Страницы списка проектов">
            <span>
              {projects.data.count} {projectCountLabel(projects.data.count)}
            </span>
            <div className="pagination__actions">
              <button
                className="button button--secondary"
                disabled={!projects.data.previous || page === 1 || projects.isFetching}
                onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                type="button"
              >
                Назад
              </button>
              <span aria-live="polite">Страница {page}</span>
              <button
                className="button button--secondary"
                disabled={!projects.data.next || projects.isFetching}
                onClick={() => setPage((currentPage) => currentPage + 1)}
                type="button"
              >
                Далее
              </button>
            </div>
          </nav>
        </>
      )}
    </main>
  );
}
