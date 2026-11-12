import type { ReactNode } from 'react';
import { Link, NavLink, useNavigate } from 'react-router';
import type { User } from '../../../entities/user';
import { useLogout } from '../../../features/auth';

export function WorkspaceShell({ user, children }: { user: User; children: ReactNode }) {
  const navigate = useNavigate();
  const logout = useLogout();

  function submitLogout() {
    logout.mutate(undefined, {
      onSuccess: () => navigate('/login', { replace: true }),
    });
  }

  return (
    <div className="workspace-shell">
      <header className="workspace-header">
        <div className="workspace-header__inner">
          <Link className="workspace-brand" to="/app/projects">
            ProjectBridge
          </Link>
          <nav aria-label="Project workspace" className="workspace-nav">
            <NavLink end to="/app/projects">
              Projects
            </NavLink>
            <NavLink to="/app/projects/archive">Archive</NavLink>
            <Link className="workspace-nav__create" to="/app/projects/new">
              New project
            </Link>
          </nav>
          <div className="workspace-account">
            <span className="workspace-account__email">{user.email}</span>
            <button
              className="button button--quiet"
              disabled={logout.isPending}
              onClick={submitLogout}
              type="button"
            >
              {logout.isPending ? 'Logging out…' : 'Log out'}
            </button>
          </div>
        </div>
        {logout.error && (
          <p className="workspace-header__error" role="alert">
            {logout.error.message}
          </p>
        )}
      </header>
      {children}
    </div>
  );
}
