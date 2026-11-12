import { useState, type FormEvent } from 'react';
import { useProjectInvitations, type InvitationStatus } from '../../../entities/invitation';
import { getApiFieldErrors } from '../../../shared/api';
import { useCreateProjectInvitation, useRevokeProjectInvitation } from '../model/mutations';

const invitationStatusLabels: Record<InvitationStatus, string> = {
  pending: 'Pending',
  expired: 'Expired',
  accepted: 'Accepted',
  revoked: 'Revoked',
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
          setStatusMessage(`Invitation sent to ${invitation.invited_email}.`);
        },
      },
    );
  }

  function revoke(invitationId: string, email: string) {
    setStatusMessage(null);
    revokeInvitation.mutate(invitationId, {
      onSuccess: () => setStatusMessage(`Invitation to ${email} revoked.`),
    });
  }

  return (
    <section className="project-panel invitation-panel" aria-labelledby="invitations-title">
      <div className="section-heading">
        <div>
          <h2 id="invitations-title">Project invitations</h2>
          <p className="section-heading__description">
            Invite one customer by email and track the invitation here.
          </p>
        </div>
      </div>

      {canManage ? (
        <form className="invitation-form" onSubmit={submitInvitation}>
          <div className="form-field">
            <label htmlFor="invitation-email">Customer email</label>
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
              {createInvitation.isPending ? 'Sending…' : 'Send invitation'}
            </button>
          </div>
          {createInvitation.isError && !emailError && (
            <p className="form-error" role="alert">
              {createInvitation.error.message || 'The invitation could not be sent. Try again.'}
            </p>
          )}
        </form>
      ) : (
        <p className="field-help invitation-readonly-note">
          Invitations can be changed while the project is Draft or Active.
        </p>
      )}

      {statusMessage && (
        <p className="success-message invitation-feedback" role="status">
          {statusMessage}
        </p>
      )}
      {revokeInvitation.isError && (
        <p className="form-error" role="alert">
          {revokeInvitation.error.message || 'The invitation could not be revoked. Try again.'}
        </p>
      )}

      {invitationsQuery.isPending ? (
        <p className="state-message invitation-loading" role="status">
          Loading invitations…
        </p>
      ) : invitationsQuery.isError ? (
        <div className="state-message state-message--error invitation-list-error" role="alert">
          <p>{invitationsQuery.error.message || 'We couldn’t load project invitations.'}</p>
          <button
            className="button button--secondary"
            disabled={invitationsQuery.isFetching}
            onClick={() => void invitationsQuery.refetch()}
            type="button"
          >
            {invitationsQuery.isFetching ? 'Loading…' : 'Try again'}
          </button>
        </div>
      ) : invitationsQuery.data?.results.length ? (
        <ul className="invitation-list" aria-label="Invitation status list">
          {invitationsQuery.data.results.map((invitation) => (
            <li className="invitation-row" key={invitation.id}>
              <div className="invitation-row__main">
                <span className="invitation-row__email">{invitation.invited_email}</span>
                <span className="invitation-row__meta">
                  Expires {formatDate(invitation.expires_at)}
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
                    Revoke invitation to {invitation.invited_email}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div className="empty-state invitation-empty-state">
          <h3>No invitations yet</h3>
          <p>Invitations you send will show their status here.</p>
        </div>
      )}
      {invitationsQuery.data && (invitationsQuery.data.previous || invitationsQuery.data.next) && (
        <nav className="pagination" aria-label="Invitation pages">
          <div className="pagination__actions">
            <button
              className="button button--secondary"
              disabled={!invitationsQuery.data.previous || invitationsQuery.isFetching}
              onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
              type="button"
            >
              Previous invitations
            </button>
            <button
              className="button button--secondary"
              disabled={!invitationsQuery.data.next || invitationsQuery.isFetching}
              onClick={() => setPage((currentPage) => currentPage + 1)}
              type="button"
            >
              Next invitations
            </button>
          </div>
        </nav>
      )}
    </section>
  );
}
