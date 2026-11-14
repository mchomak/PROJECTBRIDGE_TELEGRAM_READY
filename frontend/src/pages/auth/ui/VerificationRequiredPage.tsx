import { useState, type FormEvent } from 'react';
import { Link, useLocation } from 'react-router';
import { useResendVerification } from '../../../features/auth';
import { getApiFieldErrors } from '../../../shared/api';

type VerificationState = {
  email?: string;
  sent?: boolean;
};

export function VerificationRequiredPage() {
  const location = useLocation();
  const state = (location.state as VerificationState | null) ?? {};
  const [email, setEmail] = useState(state.email ?? '');
  const [resendSent, setResendSent] = useState(false);
  const resend = useResendVerification();
  const fieldErrors = getApiFieldErrors(resend.error);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    resend.mutate(
      { email },
      {
        onSuccess: () => setResendSent(true),
      },
    );
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="verification-required-title">
        <h1 id="verification-required-title">Подтвердите электронную почту</h1>
        <p>Подтвердите адрес электронной почты, чтобы продолжить работу в ProjectBridge.</p>
        {state.email && state.sent ? (
          <p>Мы отправили ссылку подтверждения на адрес {state.email}.</p>
        ) : (
          state.email && (
            <p>
              После подтверждения адреса войдите снова. При необходимости запросите новое письмо
              ниже.
            </p>
          )
        )}

        <form onSubmit={submit} noValidate>
          <label htmlFor="verification-email">Электронная почта</label>
          <input
            autoComplete="email"
            id="verification-email"
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
          {resend.error && Object.keys(fieldErrors).length === 0 && (
            <p role="alert">{resend.error.message}</p>
          )}
          {resendSent && (
            <p role="status">Если адрес требует подтверждения, новое письмо уже отправлено.</p>
          )}
          <button disabled={resend.isPending || !email.trim()} type="submit">
            {resend.isPending ? 'Отправка…' : 'Отправить письмо повторно'}
          </button>
        </form>

        <p>
          Уже подтвердили адрес? <Link to="/login">Войти</Link>
        </p>
      </section>
    </main>
  );
}
