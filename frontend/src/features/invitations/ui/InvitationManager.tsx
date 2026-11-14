import { useState, type FormEvent } from 'react';
import { useProjectInvitations, type InvitationStatus } from '../../../entities/invitation';
import { getApiFieldErrors } from '../../../shared/api';
import { useCreateProjectInvitation, useRevokeProjectInvitation } from '../model/mutations';

const invitationStatusLabels: Record<InvitationStatus, string> = {
  pending: 'Ожидает ответа',
  expired: 'Истекло',
  accepted: 'Принято',
  revoked: 'Отозвано',
};

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

type InvitationManagerProps = {
  projectId: string;
  canManage: boolean;
};

export function InvitationManager({ projectId, canManage }: InvitationManagerProps) {
  const [page, setPage] = useState(1);
  const invitationsQuery = useProjectInvitations(projectId, page);
  const createInvitation = useCreateProjectInvitation(projectId);
  const revokeInvitation = useRevokeProjectInvitation(projectId);
  const [invitedEmail, setInvitedEmail] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const fieldErrors = getApiFieldErrors(createInvitation.error);
  const emailError = fieldErrors.invited_email?.[0];

  function submitInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatusMessage(null);
    const email = invitedEmail.trim();
    if (!email) return;

    createInvitation.mutate(
      { invited_email: email },
      {
        onSuccess: (invitation) => {
          setInvitedEmail('');
          setStatusMessage(`Приглашение отправлено на ${invitation.invited_email}.`);
        },
      },
    );
  }

  function revoke(invitationId: string, email: string) {
    setStatusMessage(null);
    revokeInvitation.mutate(invitationId, {
      onSuccess: () => setStatusMessage(`Приглашение для ${email} отозвано.`),
    });
  }

  return (
    <section className="project-panel invitation-panel" aria-labelledby="invitations-title">
      <div className="section-heading">
        <div>
          <h2 id="invitations-title">Приглашения в проект</h2>
          <p className="section-heading__description">
            Пригласите заказчика по электронной почте и следите за статусом приглашения.
          </p>
        </div>
      </div>

      {canManage ? (
        <form className="invitation-form" onSubmit={submitInvitation}>
          <div className="form-field">
            <label htmlFor="invitation-email">Почта заказчика</label>
            <input
              aria-describedby={emailError ? 'invitation-email-error' : undefined}
              aria-invalid={Boolean(emailError)}
              autoComplete="email"
              id="invitation-email"
              onChange={(event) => setInvitedEmail(event.currentTarget.value)}
              required
              type="email"
              value={invitedEmail}
            />
            {emailError && (
              <p className="field-error" id="invitation-email-error" role="alert">
                {emailError}
              </p>
            )}
          </div>
          <div className="form-actions invitation-form__actions">
            <button
              className="button button--primary"
              disabled={createInvitation.isPending}
              type="submit"
            >
              {createInvitation.isPending ? 'Отправка…' : 'Отправить приглашение'}
            </button>
          </div>
          {createInvitation.isError && !emailError && (
            <p className="form-error" role="alert">
              {createInvitation.error.message ||
                'Не удалось отправить приглашение. Попробуйте снова.'}
            </p>
          )}
        </form>
      ) : (
        <p className="field-help invitation-readonly-note">
          Приглашения можно изменять, пока проект находится в черновике или активен.
        </p>
      )}

      {statusMessage && (
        <p className="success-message invitation-feedback" role="status">
          {statusMessage}
        </p>
      )}
      {revokeInvitation.isError && (
        <p className="form-error" role="alert">
          {revokeInvitation.error.message || 'Не удалось отозвать приглашение. Попробуйте снова.'}
        </p>
      )}

      {invitationsQuery.isPending ? (
        <p className="state-message invitation-loading" role="status">
          Загрузка приглашений…
        </p>
      ) : invitationsQuery.isError ? (
        <div className="state-message state-message--error invitation-list-error" role="alert">
          <p>{invitationsQuery.error.message || 'Не удалось загрузить приглашения проекта.'}</p>
          <button
            className="button button--secondary"
            disabled={invitationsQuery.isFetching}
            onClick={() => void invitationsQuery.refetch()}
            type="button"
          >
            {invitationsQuery.isFetching ? 'Загрузка…' : 'Попробовать снова'}
          </button>
        </div>
      ) : invitationsQuery.data?.results.length ? (
        <ul className="invitation-list" aria-label="Список приглашений">
          {invitationsQuery.data.results.map((invitation) => (
            <li className="invitation-row" key={invitation.id}>
              <div className="invitation-row__main">
                <span className="invitation-row__email">{invitation.invited_email}</span>
                <span className="invitation-row__meta">
                  Действует до {formatDate(invitation.expires_at)}
                </span>
              </div>
              <div className="invitation-row__actions">
                <span className={`status-badge status-badge--${invitation.status}`} role="status">
                  {invitationStatusLabels[invitation.status]}
                </span>
                {canManage && invitation.status === 'pending' && (
                  <button
                    className="button button--quiet invitation-revoke"
                    disabled={revokeInvitation.isPending}
                    onClick={() => revoke(invitation.id, invitation.invited_email)}
                    type="button"
                  >
                    Отозвать приглашение для {invitation.invited_email}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div className="empty-state invitation-empty-state">
          <h3>Приглашений пока нет</h3>
          <p>Здесь появятся отправленные приглашения и их статусы.</p>
        </div>
      )}
      {invitationsQuery.data && (invitationsQuery.data.previous || invitationsQuery.data.next) && (
        <nav className="pagination" aria-label="Страницы приглашений">
          <div className="pagination__actions">
            <button
              className="button button--secondary"
              disabled={!invitationsQuery.data.previous || invitationsQuery.isFetching}
              onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
              type="button"
            >
              Предыдущие приглашения
            </button>
            <button
              className="button button--secondary"
              disabled={!invitationsQuery.data.next || invitationsQuery.isFetching}
              onClick={() => setPage((currentPage) => currentPage + 1)}
              type="button"
            >
              Следующие приглашения
            </button>
          </div>
        </nav>
      )}
    </section>
  );
}
