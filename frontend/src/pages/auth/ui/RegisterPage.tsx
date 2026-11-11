import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import type { User } from '../../../entities/user';
import { useRegister } from '../../../features/auth';
import { ApiError, getApiFieldErrors } from '../../../shared/api';

export function RegisterPage() {
  const navigate = useNavigate();
  const register = useRegister();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const fieldErrors = getApiFieldErrors(register.error);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    register.mutate(
      { email, password },
      {
        onSuccess: (user: User) => {
          navigate('/verification-required', {
            replace: true,
            state: { email: user.email, sent: true },
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
      <section className="auth-card" aria-labelledby="register-title">
        <h1 id="register-title">Create an account</h1>
        <form onSubmit={submit} noValidate>
          <label htmlFor="register-email">Email</label>
          <input
            autoComplete="email"
            id="register-email"
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

          <label htmlFor="register-password">Password</label>
          <input
            autoComplete="new-password"
            id="register-password"
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

          {register.error && Object.keys(fieldErrors).length === 0 && (
            <p role="alert">{register.error.message}</p>
          )}

          <button disabled={register.isPending} type="submit">
            {register.isPending ? 'Creating account…' : 'Create account'}
          </button>
        </form>
        <p>
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </section>
    </main>
  );
}
