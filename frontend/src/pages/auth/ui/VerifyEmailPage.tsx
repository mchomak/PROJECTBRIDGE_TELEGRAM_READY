import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router';
import { useConfirmVerification } from '../../../features/auth';

export function VerifyEmailPage() {
  const location = useLocation();
  const confirm = useConfirmVerification();
  const started = useRef(false);
  const [missingToken, setMissingToken] = useState(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
    if (window.location.hash) {
      window.history.replaceState(
        window.history.state,
        '',
        `${location.pathname}${location.search}`,
      );
    }

    if (!token) {
      setMissingToken(true);
      return;
    }

    confirm.mutate({ token });
  }, [confirm.mutate, location.pathname, location.search]);

  if (confirm.data?.email_verified) {
    return (
      <main className="auth-page">
        <section className="auth-card" aria-labelledby="verification-success-title">
          <h1 id="verification-success-title">Email confirmed</h1>
          <p>Your email address is verified. Log in to continue.</p>
          <Link to="/login">Log in</Link>
        </section>
      </main>
    );
  }

  if (missingToken || confirm.error) {
    return (
      <main className="auth-page">
        <section className="auth-card" aria-labelledby="verification-error-title">
          <h1 id="verification-error-title">We couldn’t confirm this email</h1>
          <p role="alert">
            {confirm.error?.message ?? 'This verification link is missing its token.'}
          </p>
          <Link to="/verification-required">Request another verification email</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="verification-pending-title">
        <h1 id="verification-pending-title">Confirming your email…</h1>
        <p role="status">Please wait while we verify your address.</p>
      </section>
    </main>
  );
}
