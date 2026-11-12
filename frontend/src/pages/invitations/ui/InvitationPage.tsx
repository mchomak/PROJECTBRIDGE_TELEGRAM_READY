import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useId, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import {
  acceptInvitation,
  previewInvitation,
  type InvitationTokenRequest,
} from '../../../entities/invitation';
import { useCurrentUser, type User } from '../../../entities/user';
import { useLogin, useLogout, useRegister, useResendVerification } from '../../../features/auth';
import { ApiError, getApiFieldErrors } from '../../../shared/api';

function previewErrorState(error: unknown): { title: string; detail: string } {
  if (!(error instanceof ApiError)) {
    return {
      title: 'We couldn’t check this invitation',
      detail: 'Check your connection and try again.',
    };
  }

  switch (error.payload?.code) {
    case 'invitation_expired':
      return {
        title: 'This invitation has expired',
        detail: 'Ask the project executor to send a new invitation.',
      };
    case 'invitation_revoked':
      return {
        title: 'This invitation was revoked',
        detail: 'Ask the project executor for a new invitation.',
      };
    case 'project_completed':
      return {
        title: 'This project is complete',
        detail: 'Completed projects cannot accept new customers.',
      };
    case 'project_archived':
      return {
        title: 'This project is archived',
        detail: 'Archived projects cannot accept new customers.',
      };
    case 'not_found':
      return {
        title: 'This invitation link is invalid',
        detail: 'Open the invitation link from the email you received.',
      };
    case 'conflict':
      return {
        title: 'This invitation can’t be accepted',
        detail: 'The invitation or project may have changed. Ask the project executor for help.',
      };
    default:
      if (error.status === 429) {
        return {
          title: 'Too many invitation checks',
          detail: 'Wait a little while, then try again.',
        };
      }
      return {
        title: 'We couldn’t check this invitation',
        detail: error.message || 'Check your connection and try again.',
      };
  }
}

function acceptanceErrorState(error: unknown): { title: string; detail: string } {
  if (error instanceof ApiError && error.status === 429) {
    return {
      title: 'Too many acceptance attempts',
      detail: 'Wait a little while, then try again.',
    };
  }
  return previewErrorState(error);
}

function useInvitationToken() {
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('token'));
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(
        window.history.state,
        '',
        `${window.location.pathname}${window.location.search}`,
      );
    }
    setReady(true);
  }, []);

  return { token, ready };
}

export function InvitationPage() {
  const { token, ready: tokenReady } = useInvitationToken();
  const previewQueryId = useId();
  const navigate = useNavigate();
  const currentUser = useCurrentUser();
  const login = useLogin();
  const logout = useLogout();
  const register = useRegister();
  const resendVerification = useResendVerification();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [registrationMessage, setRegistrationMessage] = useState<string | null>(null);
  const errors = getApiFieldErrors(authMode === 'login' ? login.error : register.error);

  const invitation = useQuery({
    queryKey: ['publicInvitationPreview', previewQueryId],
    queryFn: () => previewInvitation(token as InvitationTokenRequest['token']),
    enabled: tokenReady && Boolean(token),
    gcTime: 0,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status < 500) return false;
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(200 * 2 ** attempt, 1000),
  });

  const acceptance = useMutation({
    mutationFn: () => acceptInvitation(token as InvitationTokenRequest['token']),
    onSuccess: (result) => navigate(`/app/projects/${result.project_id}`, { replace: true }),
  });

  function submitCredentials(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authMode === 'login') {
      login.mutate({ email, password }, { onError: clearRejectedPassword });
      return;
    }

    register.mutate(
      { email, password },
      {
        onSuccess: (user: User) => {
          setRegistrationMessage(
            `We sent a verification email to ${user.email}. Verify your email, then log in here to accept the invitation.`,
          );
          setPassword('');
          setAuthMode('login');
        },
        onError: clearRejectedPassword,
      },
    );
  }

  function clearRejectedPassword(error: Error) {
    if (error instanceof ApiError && error.status === 400) setPassword('');
  }

  function switchAuthMode(mode: 'login' | 'register') {
    login.reset();
    register.reset();
    setRegistrationMessage(null);
    setPassword('');
    setAuthMode(mode);
  }

  function accept() {
    acceptance.mutate();
  }

  const tokenLoaded = tokenReady && token !== null;
  const signedOut =
    currentUser.isError &&
    currentUser.error instanceof ApiError &&
    currentUser.error.status === 401;
  const acceptingError =
    acceptance.error instanceof ApiError ? acceptance.error.payload?.code : null;
  const terminalAcceptanceError =
    acceptance.error instanceof ApiError && [404, 409, 410].includes(acceptance.error.status);
  const fieldErrors = errors;
  const authError = authMode === 'login' ? login.error : register.error;

  return (
    <main className="auth-page">
      <section className="auth-card invitation-card" aria-labelledby="invitation-title">
        {!tokenReady ? (
          <p className="state-message" role="status">
            Opening invitation…
          </p>
        ) : !tokenLoaded ? (
          <>
            <h1 id="invitation-title">Invitation link not found</h1>
            <p>Open the invitation link from the email you received.</p>
          </>
        ) : invitation.isPending ? (
          <p className="state-message" role="status">
            Checking invitation…
          </p>
        ) : invitation.isError ? (
          <>
            <h1 id="invitation-title">{previewErrorState(invitation.error).title}</h1>
            <p role="alert">{previewErrorState(invitation.error).detail}</p>
            <button
              className="button button--secondary"
              onClick={() => void invitation.refetch()}
              type="button"
            >
              Try again
            </button>
          </>
        ) : invitation.data ? (
          <>
            <h1 id="invitation-title">
              {invitation.data.status === 'accepted'
                ? `You’re already invited to ${invitation.data.project_name}`
                : `You’re invited to ${invitation.data.project_name}`}
            </h1>
            <p>
              Invitation for <strong>{invitation.data.email_hint}</strong>. Expires{' '}
              {new Date(invitation.data.expires_at).toLocaleString()}.
            </p>

            {currentUser.isPending && (
              <p className="state-message" role="status">
                Checking your sign-in…
              </p>
            )}

            {currentUser.isError && !signedOut && (
              <div className="state-message state-message--error" role="alert">
                <p>We couldn’t check your sign-in.</p>
                <p>{currentUser.error.message}</p>
                <button
                  className="button button--secondary"
                  onClick={() => void currentUser.refetch()}
                  type="button"
                >
                  Try again
                </button>
              </div>
            )}

            {signedOut && (
              <>
                <h2>{authMode === 'login' ? 'Log in to accept' : 'Create an account'}</h2>
                {registrationMessage && <p role="status">{registrationMessage}</p>}
                <form onSubmit={submitCredentials} noValidate>
                  <label htmlFor="invitation-email">Email</label>
                  <input
                    autoComplete="email"
                    id="invitation-email"
                    name="email"
                    onChange={(event) => setEmail(event.currentTarget.value)}
                    required
                    type="email"
                    value={email}
                  />
                  {fieldErrors.email?.map((message) => (
                    <p className="field-error" key={message} role="alert">
                      {message}
                    </p>
                  ))}
                  <label htmlFor="invitation-password">Password</label>
                  <input
                    autoComplete={authMode === 'login' ? 'current-password' : 'new-password'}
                    id="invitation-password"
                    name="password"
                    onChange={(event) => setPassword(event.currentTarget.value)}
                    required
                    type="password"
                    value={password}
                  />
                  {fieldErrors.password?.map((message) => (
                    <p className="field-error" key={message} role="alert">
                      {message}
                    </p>
                  ))}
                  {authError && Object.keys(fieldErrors).length === 0 && (
                    <p role="alert">{authError.message}</p>
                  )}
                  <button
                    className="button button--primary"
                    disabled={login.isPending || register.isPending}
                    type="submit"
                  >
                    {login.isPending || register.isPending
                      ? authMode === 'login'
                        ? 'Logging in…'
                        : 'Creating account…'
                      : authMode === 'login'
                        ? 'Log in'
                        : 'Create account'}
                  </button>
                </form>
                <p>
                  {authMode === 'login' ? 'New to ProjectBridge?' : 'Already have an account?'}{' '}
                  <button
                    className="button button--secondary"
                    onClick={() => switchAuthMode(authMode === 'login' ? 'register' : 'login')}
                    type="button"
                  >
                    {authMode === 'login' ? 'Create an account' : 'Log in'}
                  </button>
                </p>
              </>
            )}

            {currentUser.data && !currentUser.data.email_verified && (
              <section aria-labelledby="verify-invited-email-title">
                <h2 id="verify-invited-email-title">Verify your email to continue</h2>
                <p>Accepting requires a verified account for the invited email address.</p>
                <button
                  className="button button--secondary"
                  disabled={resendVerification.isPending}
                  onClick={() => resendVerification.mutate({ email: currentUser.data.email })}
                  type="button"
                >
                  {resendVerification.isPending ? 'Sending…' : 'Resend verification email'}
                </button>
                {resendVerification.isSuccess && (
                  <p role="status">Check your inbox for the verification email.</p>
                )}
                {resendVerification.isError && (
                  <p role="alert">{resendVerification.error.message}</p>
                )}
                <button
                  className="button button--secondary"
                  onClick={() => void currentUser.refetch()}
                  type="button"
                >
                  I’ve verified my email
                </button>
              </section>
            )}

            {currentUser.data?.email_verified && (
              <>
                {acceptingError === 'email_mismatch' && (
                  <div className="state-message state-message--error" role="alert">
                    <p>
                      This invitation belongs to {invitation.data.email_hint}. Sign in with that
                      verified email.
                    </p>
                    <button
                      className="button button--secondary"
                      disabled={logout.isPending}
                      onClick={() => logout.mutate()}
                      type="button"
                    >
                      {logout.isPending ? 'Signing out…' : 'Use another account'}
                    </button>
                  </div>
                )}
                {acceptingError === 'email_unverified' && (
                  <div role="alert">
                    <p>Verify the email address on this account before accepting the invitation.</p>
                    <button
                      className="button button--secondary"
                      onClick={() => void currentUser.refetch()}
                      type="button"
                    >
                      I’ve verified my email
                    </button>
                  </div>
                )}
                {acceptance.error &&
                  acceptingError !== 'email_mismatch' &&
                  acceptingError !== 'email_unverified' && (
                    <div role="alert">
                      <p>{acceptanceErrorState(acceptance.error).title}</p>
                      <p>{acceptanceErrorState(acceptance.error).detail}</p>
                    </div>
                  )}
                {!terminalAcceptanceError && (
                  <button
                    className="button button--primary"
                    disabled={acceptance.isPending}
                    onClick={accept}
                    type="button"
                  >
                    {acceptance.isPending
                      ? 'Accepting…'
                      : invitation.data.status === 'accepted'
                        ? 'Open project'
                        : 'Accept invitation'}
                  </button>
                )}
              </>
            )}
          </>
        ) : null}
      </section>
    </main>
  );
}
