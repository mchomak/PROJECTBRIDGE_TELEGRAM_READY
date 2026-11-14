import { type ReactNode, useEffect } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router';
import { useProject, useProjectMembers } from '../../../entities/project';
import type { User } from '../../../entities/user';
import { useLogout } from '../../../features/auth';

function Icon({
  name,
}: {
  name: 'grid' | 'archive' | 'plus' | 'folder' | 'chat' | 'state' | 'form' | 'document' | 'spark';
}) {
  const paths = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    archive: (
      <>
        <path d="M4 7h16v13H4zM3 4h18v3H3zM9 11h6" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    folder: <path d="M3 6h7l2 2h9v11H3z" />,
    chat: <path d="M4 4h16v12H9l-5 4z" />,
    state: (
      <>
        <path d="M9 6h12M9 12h12M9 18h12" />
        <path d="m3 6 1 1 2-2M3 12l1 1 2-2M3 18l1 1 2-2" />
      </>
    ),
    form: (
      <>
        <rect x="5" y="3" width="14" height="18" rx="2" />
        <path d="M9 8h6M9 12h6M9 16h4" />
      </>
    ),
    document: (
      <>
        <path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6M9 16h6" />
      </>
    ),
    spark: <path d="m12 3 2.1 5.9L20 11l-5.9 2.1L12 19l-2.1-5.9L4 11l5.9-2.1z" />,
  };
  return (
    <svg
      aria-hidden="true"
      className="workspace-nav__icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

export function WorkspaceShell({ user, children }: { user: User; children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useLogout();
  const projectId = location.pathname.match(/^\/app\/projects\/([^/]+)(?:\/|$)/)?.[1] ?? '';
  const selectedId = projectId === 'new' || projectId === 'archive' ? '' : projectId;
  const project = useProject(selectedId);
  const members = useProjectMembers(selectedId);
  const member = members.data?.find((candidate) => candidate.user_id === user.id);
  const base = `/app/projects/${selectedId}`;
  const documentsActive = location.pathname === base && location.hash === '#documents';
  const overviewActive = location.pathname === base && !documentsActive;
  const isChat = location.pathname === `${base}/chat`;

  useEffect(() => {
    if (location.hash !== '#documents' || location.pathname !== base) return;
    const scrollToDocuments = () => {
      const element = document.getElementById('documents');
      if (!element) return false;
      element.scrollIntoView();
      return true;
    };
    if (scrollToDocuments()) return;
    const observer = new MutationObserver(() => {
      if (scrollToDocuments()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [base, location.pathname, location.hash]);
  function submitLogout() {
    logout.mutate(undefined, { onSuccess: () => navigate('/login', { replace: true }) });
  }

  return (
    <div className="workspace-shell">
      <a className="workspace-skip-link" href="#workspace-content">
        Перейти к содержимому
      </a>
      <aside className="workspace-header">
        <div className="workspace-header__inner">
          <Link className="workspace-brand" to="/app/projects">
            <span className="workspace-brand__symbol">P</span>
            <span>
              projectbridge<span className="workspace-brand__dot">.</span>
            </span>
          </Link>
          <nav aria-label="Рабочее пространство" className="workspace-nav">
            <span className="workspace-nav__caption">Рабочее пространство</span>
            <NavLink end to="/app/projects">
              <Icon name="grid" />
              Мои проекты
            </NavLink>
            <NavLink to="/app/projects/archive">
              <Icon name="archive" />
              Архив
            </NavLink>
            <Link to="/app/projects/new">
              <Icon name="plus" />
              Новый проект
            </Link>
            {selectedId && member && project.data && (
              <>
                <span className="workspace-nav__caption">Активный проект</span>
                <Link className="workspace-project" to={base}>
                  <Icon name="folder" />
                  <span>{project.data.name}</span>
                </Link>
                <Link to={base} aria-current={overviewActive ? 'page' : undefined}>
                  <Icon name="grid" />
                  Обзор
                </Link>
                <NavLink to={`${base}/chat`}>
                  <Icon name="chat" />
                  Чат
                </NavLink>
                <NavLink to={`${base}/state`}>
                  <Icon name="state" />
                  Состояние проекта
                </NavLink>
                <NavLink to={`${base}/questionnaire`}>
                  <Icon name="form" />
                  Анкета
                </NavLink>
                <Link
                  to={`${base}#documents`}
                  aria-current={documentsActive ? 'page' : undefined}
                  onClick={() => document.getElementById('documents')?.scrollIntoView()}
                >
                  <Icon name="folder" />
                  Документы
                </Link>
                <NavLink to={`${base}/specification`}>
                  <Icon name="document" />
                  Спецификация
                </NavLink>
                {member.role === 'executor' && (
                  <NavLink to={`${base}/ai`}>
                    <Icon name="spark" />
                    AI-анализ
                  </NavLink>
                )}
              </>
            )}
          </nav>
          <div className="workspace-account">
            <span className="workspace-account__avatar" aria-hidden="true">
              {user.email.charAt(0).toUpperCase()}
            </span>
            <span className="workspace-account__email" title={user.email}>
              {user.email}
            </span>
            <button
              className="button button--quiet"
              disabled={logout.isPending}
              onClick={submitLogout}
              type="button"
            >
              {logout.isPending ? 'Выход…' : 'Выйти'}
            </button>
          </div>
          {logout.error && (
            <p className="workspace-header__error" role="alert">
              {logout.error.message}
            </p>
          )}
        </div>
      </aside>
      <div className="workspace-content" id="workspace-content" tabIndex={-1}>
        {selectedId && member && project.data && (
          <header className="project-shell-header">
            <div className="project-shell-header__heading">
              <div>
                <h1>{project.data.name}</h1>
                {project.data.description && <p>{project.data.description}</p>}
              </div>
            </div>
            <nav className="project-tabs" aria-label="Разделы проекта">
              <Link to={base} aria-current={overviewActive ? 'page' : undefined}>
                Обзор
              </Link>
              <NavLink to={`${base}/chat`}>Чат</NavLink>
              <NavLink to={`${base}/state`}>Состояние проекта</NavLink>
              <NavLink to={`${base}/questionnaire`}>Анкета</NavLink>
              <Link
                to={`${base}#documents`}
                aria-current={documentsActive ? 'page' : undefined}
                onClick={() => document.getElementById('documents')?.scrollIntoView()}
              >
                Документы
              </Link>
              <NavLink to={`${base}/specification`}>Спецификация</NavLink>
              {member.role === 'executor' && <NavLink to={`${base}/ai`}>AI-анализ</NavLink>}
            </nav>
          </header>
        )}
        <div className={isChat && member && project.data ? 'workspace-chat-layout' : undefined}>
          {children}
          {isChat && member && project.data && (
            <aside className="workspace-chat-rail" aria-label="Материалы проекта">
              <h2>{member.role === 'executor' ? 'AI-помощник' : 'Состояние проекта'}</h2>
              <p>
                {member.role === 'executor'
                  ? 'Анализ и предложения доступны исполнителю в отдельном разделе.'
                  : 'Общая информация и документы доступны участникам проекта.'}
              </p>
              {member.role === 'executor' ? (
                <Link to={`${base}/ai`}>Открыть AI-анализ →</Link>
              ) : (
                <Link to={`${base}/state`}>Открыть состояние проекта →</Link>
              )}
              <Link to={`${base}#documents`}>Открыть документы →</Link>
            </aside>
          )}
        </div>
      </div>{' '}
    </div>
  );
}
