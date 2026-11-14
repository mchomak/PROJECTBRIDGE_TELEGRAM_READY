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
          <h1 id="verification-success-title">Адрес электронной почты подтверждён</h1>
          <p>Адрес подтверждён. Войдите, чтобы продолжить.</p>
          <Link to="/login">Войти</Link>
        </section>
      </main>
    );
  }

  if (missingToken || confirm.error) {
    return (
      <main className="auth-page">
        <section className="auth-card" aria-labelledby="verification-error-title">
          <h1 id="verification-error-title">Не удалось подтвердить адрес</h1>
          <p role="alert">
            {confirm.error?.message ?? 'В ссылке подтверждения отсутствует токен.'}
          </p>
          <Link to="/verification-required">Запросить новое письмо</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="verification-pending-title">
        <h1 id="verification-pending-title">Подтверждаем адрес…</h1>
        <p role="status">Подождите, пока мы проверяем адрес.</p>
      </section>
    </main>
  );
}
