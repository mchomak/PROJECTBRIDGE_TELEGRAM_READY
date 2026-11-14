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
      title: 'Не удалось проверить приглашение',
      detail: 'Проверьте подключение и попробуйте снова.',
    };
  }

  switch (error.payload?.code) {
    case 'invitation_expired':
      return {
        title: 'Срок действия приглашения истёк',
        detail: 'Попросите исполнителя отправить новое приглашение.',
      };
    case 'invitation_revoked':
      return {
        title: 'Приглашение отозвано',
        detail: 'Попросите исполнителя отправить новое приглашение.',
      };
    case 'project_completed':
      return {
        title: 'Проект завершён',
        detail: 'В завершённый проект нельзя пригласить нового заказчика.',
      };
    case 'project_archived':
      return {
        title: 'Проект в архиве',
        detail: 'В архивный проект нельзя пригласить нового заказчика.',
      };
    case 'not_found':
      return {
        title: 'Ссылка приглашения недействительна',
        detail: 'Откройте ссылку приглашения из полученного письма.',
      };
    case 'conflict':
      return {
        title: 'Не удалось принять приглашение',
        detail: 'Возможно, приглашение или проект изменились. Обратитесь к исполнителю.',
      };
    default:
      if (error.status === 429) {
        return {
          title: 'Слишком много проверок приглашения',
          detail: 'Подождите немного и попробуйте снова.',
        };
      }
      return {
        title: 'Не удалось проверить приглашение',
        detail: error.message || 'Проверьте подключение и попробуйте снова.',
      };
  }
}

function acceptanceErrorState(error: unknown): { title: string; detail: string } {
  if (error instanceof ApiError && error.status === 429) {
    return {
      title: 'Слишком много попыток принятия',
      detail: 'Подождите немного и попробуйте снова.',
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
            Открываем приглашение…
          </p>
        ) : !tokenLoaded ? (
          <>
            <h1 id="invitation-title">Ссылка приглашения не найдена</h1>
            <p>Откройте ссылку приглашения из полученного письма.</p>
          </>
        ) : invitation.isPending ? (
          <p className="state-message" role="status">
            Проверяем приглашение…
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
              Попробовать снова
            </button>
          </>
        ) : invitation.data ? (
          <>
            <h1 id="invitation-title">
              {invitation.data.status === 'accepted'
                ? `Вы уже приглашены в проект «${invitation.data.project_name}»`
                : `Вас пригласили в проект «${invitation.data.project_name}»`}
            </h1>
            <p>
              Приглашение для <strong>{invitation.data.email_hint}</strong>. Действует до{' '}
              {new Date(invitation.data.expires_at).toLocaleString()}.
            </p>

            {currentUser.isPending && (
              <p className="state-message" role="status">
                Проверяем вход…
              </p>
            )}

            {currentUser.isError && !signedOut && (
              <div className="state-message state-message--error" role="alert">
                <p>Не удалось проверить вход в аккаунт.</p>
                <p>{currentUser.error.message}</p>
                <button
                  className="button button--secondary"
                  onClick={() => void currentUser.refetch()}
                  type="button"
                >
                  Попробовать снова
                </button>
              </div>
            )}

            {signedOut && (
              <>
                <h2>
                  {authMode === 'login' ? 'Войдите, чтобы принять приглашение' : 'Создать аккаунт'}
                </h2>
                {registrationMessage && <p role="status">{registrationMessage}</p>}
                <form onSubmit={submitCredentials} noValidate>
                  <label htmlFor="invitation-email">Электронная почта</label>
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
                  <label htmlFor="invitation-password">Пароль</label>
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
                        ? 'Вход…'
                        : 'Создание аккаунта…'
                      : authMode === 'login'
                        ? 'Войти'
                        : 'Создать аккаунт'}
                  </button>
                </form>
                <p>
                  {authMode === 'login' ? 'Впервые в ProjectBridge?' : 'Уже есть аккаунт?'}{' '}
                  <button
                    className="button button--secondary"
                    onClick={() => switchAuthMode(authMode === 'login' ? 'register' : 'login')}
                    type="button"
                  >
                    {authMode === 'login' ? 'Создать аккаунт' : 'Войти'}
                  </button>
                </p>
              </>
            )}

            {currentUser.data && !currentUser.data.email_verified && (
              <section aria-labelledby="verify-invited-email-title">
                <h2 id="verify-invited-email-title">
                  Подтвердите адрес электронной почты, чтобы продолжить
                </h2>
                <p>Для принятия приглашения подтвердите адрес, на который оно отправлено.</p>
                <button
                  className="button button--secondary"
                  disabled={resendVerification.isPending}
                  onClick={() => resendVerification.mutate({ email: currentUser.data.email })}
                  type="button"
                >
                  {resendVerification.isPending ? 'Отправка…' : 'Отправить письмо повторно'}
                </button>
                {resendVerification.isSuccess && (
                  <p role="status">Проверьте почту: мы отправили письмо для подтверждения.</p>
                )}
                {resendVerification.isError && (
                  <p role="alert">{resendVerification.error.message}</p>
                )}
                <button
                  className="button button--secondary"
                  onClick={() => void currentUser.refetch()}
                  type="button"
                >
                  Я подтвердил адрес
                </button>
              </section>
            )}

            {currentUser.data?.email_verified && (
              <>
                {acceptingError === 'email_mismatch' && (
                  <div className="state-message state-message--error" role="alert">
                    <p>
                      Это приглашение предназначено для {invitation.data.email_hint}. Sign in with
                      that verified email.
                    </p>
                    <button
                      className="button button--secondary"
                      disabled={logout.isPending}
                      onClick={() => logout.mutate()}
                      type="button"
                    >
                      {logout.isPending ? 'Выход…' : 'Использовать другой аккаунт'}
                    </button>
                  </div>
                )}
                {acceptingError === 'email_unverified' && (
                  <div role="alert">
                    <p>Подтвердите адрес этого аккаунта, прежде чем принять приглашение.</p>
                    <button
                      className="button button--secondary"
                      onClick={() => void currentUser.refetch()}
                      type="button"
                    >
                      Я подтвердил адрес
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
                      ? 'Принимаем приглашение…'
                      : invitation.data.status === 'accepted'
                        ? 'Открыть проект'
                        : 'Принять приглашение'}
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
