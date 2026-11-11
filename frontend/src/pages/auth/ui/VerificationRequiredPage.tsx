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
        <h1 id="verification-required-title">Verify your email</h1>
        <p>Confirm your email address to continue to ProjectBridge.</p>
        {state.email && state.sent ? (
          <p>We sent a verification link to {state.email}.</p>
        ) : (
          state.email && (
            <p>
              After you verify your email, log in again to continue. If you need a verification
              email, request one below.
            </p>
          )
        )}

        <form onSubmit={submit} noValidate>
          <label htmlFor="verification-email">Email</label>
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
            <p role="status">If that address needs verification, a new message is on its way.</p>
          )}
          <button disabled={resend.isPending || !email.trim()} type="submit">
            {resend.isPending ? 'Sending…' : 'Resend verification email'}
          </button>
        </form>

        <p>
          Already verified? <Link to="/login">Log in</Link>
        </p>
      </section>
    </main>
  );
}
