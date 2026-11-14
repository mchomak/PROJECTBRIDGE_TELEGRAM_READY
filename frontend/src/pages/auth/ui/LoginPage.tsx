import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { useLogin } from '../../../features/auth';
import type { User } from '../../../entities/user';
import { ApiError, getApiFieldErrors } from '../../../shared/api';

export function LoginPage() {
  const navigate = useNavigate();
  const login = useLogin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const fieldErrors = getApiFieldErrors(login.error);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    login.mutate(
      { email, password },
      {
        onSuccess: (user: User) => {
          navigate(user.email_verified ? '/app' : '/verification-required', {
            replace: true,
            state: { email: user.email },
          });
        },
        onError: (error) => {
          if (error instanceof ApiError && error.status === 400) setPassword('');
        },
      },
    );
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="login-title">
        <h1 id="login-title">Войти</h1>
        <form onSubmit={submit} noValidate>
          <label htmlFor="login-email">Электронная почта</label>
          <input
            autoComplete="email"
            id="login-email"
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

          <label htmlFor="login-password">Пароль</label>
          <input
            autoComplete="current-password"
            id="login-password"
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

          {login.error && Object.keys(fieldErrors).length === 0 && (
            <p role="alert">{login.error.message}</p>
          )}

          <button disabled={login.isPending} type="submit">
            {login.isPending ? 'Вход…' : 'Войти'}
          </button>
        </form>
        <p>
          Впервые в ProjectBridge? <Link to="/register">Создать аккаунт</Link>
        </p>
      </section>
    </main>
  );
}
