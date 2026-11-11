import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router';
import { currentUserQueryKey, useCurrentUser, type User } from '../entities/user';
import { useLogout } from '../features/auth';
import { LoginPage, RegisterPage, VerificationRequiredPage, VerifyEmailPage } from '../pages/auth';
import { HomePage } from '../pages/home';
import { NotFoundPage } from '../pages/not-found';
import { ApiError } from '../shared/api';

function ProtectedAppPage() {
  const queryClient = useQueryClient();
  const location = useLocation();
  const { data: user, error, isError, isPending, refetch } = useCurrentUser();

  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) {
      queryClient.removeQueries({ queryKey: currentUserQueryKey, exact: true });
    }
  }, [error, queryClient]);

  if (isPending) {
    return (
      <main>
        <p role="status">Loading your account…</p>
      </main>
    );
  }

  if (isError && error instanceof ApiError && error.status === 401) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (isError) {
    return (
      <main>
        <section aria-labelledby="account-error-title">
          <h1 id="account-error-title">We couldn’t load your account</h1>
          <p role="alert">{error.message || 'Check your connection and try again.'}</p>
          <button onClick={() => void refetch()} type="button">
            Try again
          </button>
        </section>
      </main>
    );
  }

  if (user && !user.email_verified) {
    return <Navigate to="/verification-required" replace state={{ email: user.email }} />;
  }

  return user ? <AuthenticatedPage user={user} /> : null;
}

function AuthenticatedPage({ user }: { user: User }) {
  const navigate = useNavigate();
  const logout = useLogout();

  function submitLogout() {
    logout.mutate(undefined, {
      onSuccess: () => navigate('/login', { replace: true }),
    });
  }

  return (
    <main>
      <section aria-labelledby="account-title">
        <h1 id="account-title">Your account</h1>
        <p>Signed in as {user.email}</p>
        <button disabled={logout.isPending} onClick={submitLogout} type="button">
          {logout.isPending ? 'Logging out…' : 'Log out'}
        </button>
        {logout.error && <p role="alert">{logout.error.message}</p>}
      </section>
    </main>
  );
}

export function App() {
  const queryClient = useMemo(() => new QueryClient(), []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/app" element={<ProtectedAppPage />} />
          <Route path="/verification-required" element={<VerificationRequiredPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
