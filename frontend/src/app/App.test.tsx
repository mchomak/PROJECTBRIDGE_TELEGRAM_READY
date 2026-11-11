import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from './App';

afterEach(() => {
  window.history.replaceState({}, '', '/');
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test('the root route renders the minimal application shell', async () => {
  window.history.replaceState({}, '', '/');
  render(<App />);

  expect(screen.getByRole('main').textContent).toContain('ProjectBridge');
});

test('an unmatched route renders a not-found state', async () => {
  window.history.replaceState({}, '', '/unmatched-route');
  render(<App />);

  expect(screen.getByRole('heading', { name: 'Page not found' })).toBeTruthy();
});

test('the login route renders an accessible credentials form', async () => {
  window.history.replaceState({}, '', '/login');
  render(<App />);

  expect(screen.getByRole('heading', { name: 'Log in' })).toBeTruthy();
  expect(screen.getByLabelText('Email')).toBeTruthy();
  expect(screen.getByLabelText('Password')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Log in' })).toBeTruthy();
});

test('successful login loads the authenticated account without storing credentials', async () => {
  window.history.replaceState({}, '', '/login');
  const user = {
    id: 'c6d93bb6-8449-49b5-98cc-dc65f4ba78ab',
    email: 'verified@example.com',
    first_name: '',
    last_name: '',
    email_verified: true,
    email_verified_at: '2026-11-11T00:00:00Z',
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=csrf-token-value',
      });
      return new Response(JSON.stringify({ csrf_token: 'csrf-token-value' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (String(input) === '/api/v1/auth/login/') {
      expect(JSON.parse(String(init?.body))).toEqual({
        email: 'verified@example.com',
        password: 'correct-horse-battery',
      });
      expect(new Headers(init?.headers).get('X-CSRFToken')).toBe('csrf-token-value');
      return new Response(JSON.stringify(user), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    expect(String(input)).toBe('/api/v1/auth/me/');
    return new Response(JSON.stringify(user), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  });
  const localStorageWrite = vi.spyOn(window.localStorage, 'setItem');
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'verified@example.com' },
  });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'correct-horse-battery' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }));

  expect(await screen.findByRole('heading', { name: 'Your account' })).toBeTruthy();
  expect(screen.getByText('Signed in as verified@example.com')).toBeTruthy();
  expect(fetchMock.mock.calls.some(([input]) => String(input) === '/api/v1/auth/login/')).toBe(
    true,
  );
  expect(localStorageWrite).not.toHaveBeenCalled();
});

test('unverified login stays in the verification flow', async () => {
  window.history.replaceState({}, '', '/login');
  const unverifiedUser = {
    id: 'c6d93bb6-8449-49b5-98cc-dc65f4ba78ab',
    email: 'new-user@example.com',
    first_name: '',
    last_name: '',
    email_verified: false,
    email_verified_at: null,
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=csrf-token-value',
      });
      return new Response(JSON.stringify({ csrf_token: 'csrf-token-value' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    expect(String(input)).toBe('/api/v1/auth/login/');
    return new Response(JSON.stringify(unverifiedUser), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'new-user@example.com' },
  });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'unverified-account-password' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }));

  expect(await screen.findByRole('heading', { name: 'Verify your email' })).toBeTruthy();
  expect(screen.getByLabelText('Email')).toHaveProperty('value', 'new-user@example.com');
  expect(
    screen.getByText(
      'After you verify your email, log in again to continue. If you need a verification email, request one below.',
    ),
  ).toBeTruthy();
  expect(screen.queryByText(/We sent a verification link to/)).toBeNull();
  expect(fetchMock.mock.calls.some(([input]) => String(input) === '/api/v1/auth/me/')).toBe(false);
});

test('resending verification keeps the email and can be retried after a server error', async () => {
  window.history.replaceState({}, '', '/verification-required');
  let resendAttempts = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=csrf-token-value',
      });
      return new Response(JSON.stringify({ csrf_token: 'csrf-token-value' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    expect(String(input)).toBe('/api/v1/auth/email-verification/resend/');
    expect(JSON.parse(String(init?.body))).toEqual({ email: 'new-user@example.com' });
    resendAttempts += 1;
    if (resendAttempts === 1) {
      return new Response(
        JSON.stringify({
          code: 'service_unavailable',
          detail: 'The verification service is temporarily unavailable.',
          errors: null,
          request_id: '0c3054f6-558f-4264-9eb7-b48c4c693fdb',
        }),
        { status: 503, headers: { 'Content-Type': 'application/json' } },
      );
    }

    return new Response(
      JSON.stringify({ detail: 'If verification is needed, an email is on its way.' }),
      {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      },
    );
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'new-user@example.com' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Resend verification email' }));

  expect(
    await screen.findByText('The verification service is temporarily unavailable.'),
  ).toBeTruthy();
  expect(screen.getByLabelText('Email')).toHaveProperty('value', 'new-user@example.com');
  fireEvent.click(screen.getByRole('button', { name: 'Resend verification email' }));

  expect((await screen.findByRole('status')).textContent).toContain(
    'If that address needs verification, a new message is on its way.',
  );
  expect(screen.getByLabelText('Email')).toHaveProperty('value', 'new-user@example.com');
  expect(resendAttempts).toBe(2);
});

test('successful registration opens verification-required without creating a session', async () => {
  window.history.replaceState({}, '', '/register');
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=csrf-token-value',
      });
      return new Response(JSON.stringify({ csrf_token: 'csrf-token-value' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    expect(String(input)).toBe('/api/v1/auth/register/');
    expect(new Headers(init?.headers).get('X-CSRFToken')).toBe('csrf-token-value');
    expect(JSON.parse(String(init?.body))).toEqual({
      email: 'new-user@example.com',
      password: 'strong-password-42',
    });
    return new Response(
      JSON.stringify({
        id: 'c6d93bb6-8449-49b5-98cc-dc65f4ba78ab',
        email: 'new-user@example.com',
        first_name: '',
        last_name: '',
        email_verified: false,
        email_verified_at: null,
      }),
      { status: 201, headers: { 'Content-Type': 'application/json' } },
    );
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'new-user@example.com' },
  });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'strong-password-42' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }));

  expect(await screen.findByRole('heading', { name: 'Verify your email' })).toBeTruthy();
  expect(screen.getByText('We sent a verification link to new-user@example.com.')).toBeTruthy();
  expect(fetchMock.mock.calls.some(([input]) => String(input) === '/api/v1/auth/me/')).toBe(false);
});

test('logout returns to login and a later protected visit fetches the session again', async () => {
  window.history.replaceState({}, '', '/app');
  let currentUserRequests = 0;
  const user = {
    id: 'c6d93bb6-8449-49b5-98cc-dc65f4ba78ab',
    email: 'verified@example.com',
    first_name: '',
    last_name: '',
    email_verified: true,
    email_verified_at: '2026-11-11T00:00:00Z',
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=csrf-token-value',
      });
      return new Response(JSON.stringify({ csrf_token: 'csrf-token-value' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (String(input) === '/api/v1/auth/me/') {
      currentUserRequests += 1;
      if (currentUserRequests === 1) {
        return new Response(JSON.stringify(user), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(
        JSON.stringify({
          code: 'not_authenticated',
          detail: 'Authentication credentials were not provided.',
          errors: null,
          request_id: '0c3054f6-558f-4264-9eb7-b48c4c693fdb',
        }),
        { status: 401, headers: { 'Content-Type': 'application/json' } },
      );
    }

    expect(String(input)).toBe('/api/v1/auth/logout/');
    expect(init?.method).toBe('POST');
    expect(new Headers(init?.headers).get('X-CSRFToken')).toBe('csrf-token-value');
    return new Response(null, { status: 204 });
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  expect(await screen.findByRole('heading', { name: 'Your account' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Log out' }));
  expect(await screen.findByRole('heading', { name: 'Log in' })).toBeTruthy();
  expect(window.location.pathname).toBe('/login');

  window.history.pushState({}, '', '/app');
  window.dispatchEvent(new PopStateEvent('popstate'));

  await waitFor(() => expect(currentUserRequests).toBe(2));
  expect(await screen.findByRole('heading', { name: 'Log in' })).toBeTruthy();
  expect(window.location.pathname).toBe('/login');
});

test('an expired session clears the user query and redirects protected navigation to login', async () => {
  window.history.replaceState({}, '', '/app');
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        code: 'not_authenticated',
        detail: 'Authentication credentials were not provided.',
        errors: null,
        request_id: '0c3054f6-558f-4264-9eb7-b48c4c693fdb',
      }),
      { status: 401, headers: { 'Content-Type': 'application/json' } },
    ),
  );
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  await waitFor(() => expect(window.location.pathname).toBe('/login'));
  expect(fetchMock).toHaveBeenCalledWith(
    '/api/v1/auth/me/',
    expect.objectContaining({ credentials: 'same-origin', method: 'GET' }),
  );
});

test('an unverified user is sent to the verification-required page with their email', async () => {
  window.history.replaceState({}, '', '/app');
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        id: 'c6d93bb6-8449-49b5-98cc-dc65f4ba78ab',
        email: 'new-user@example.com',
        first_name: '',
        last_name: '',
        email_verified: false,
        email_verified_at: null,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ),
  );
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  await waitFor(() => expect(window.location.pathname).toBe('/verification-required'));
  expect(await screen.findByRole('heading', { name: 'Verify your email' })).toBeTruthy();
  expect(screen.getByLabelText('Email')).toHaveProperty('value', 'new-user@example.com');
});

test('the registration route renders an accessible account form', async () => {
  window.history.replaceState({}, '', '/register');
  const appModule = await import('./App').catch(() => null);
  expect(appModule).not.toBeNull();
  if (!appModule) return;

  render(<appModule.App />);

  expect(screen.getByRole('heading', { name: 'Create an account' })).toBeTruthy();
  expect(screen.getByLabelText('Email')).toBeTruthy();
  expect(screen.getByLabelText('Password')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Create account' })).toBeTruthy();
});

test('verification consumes the URL fragment once and removes it before posting', async () => {
  window.history.replaceState({}, '', '/verify-email#token=raw-verification-token');
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=csrf-token-value',
      });
      return new Response(JSON.stringify({ csrf_token: 'csrf-token-value' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    expect(String(input)).toBe('/api/v1/auth/email-verification/confirm/');
    expect(window.location.hash).toBe('');
    return new Response(
      JSON.stringify({ email_verified: true, email_verified_at: '2026-11-11T00:00:00Z' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  expect(await screen.findByRole('heading', { name: 'Email confirmed' })).toBeTruthy();
  expect(window.location.hash).toBe('');
  expect(fetchMock).toHaveBeenCalledTimes(2);
  const confirmOptions = fetchMock.mock.calls[1]?.[1] as RequestInit;
  expect(JSON.parse(String(confirmOptions.body))).toEqual({ token: 'raw-verification-token' });
  expect(screen.queryByText(/raw-verification-token/)).toBeNull();
});

test('an expired verification token shows recovery without restoring it to the URL', async () => {
  window.history.replaceState({}, '', '/verify-email#token=expired-verification-token');
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=csrf-token-value',
      });
      return new Response(JSON.stringify({ csrf_token: 'csrf-token-value' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    expect(String(input)).toBe('/api/v1/auth/email-verification/confirm/');
    expect(window.location.hash).toBe('');
    expect(JSON.parse(String(init?.body))).toEqual({ token: 'expired-verification-token' });
    return new Response(
      JSON.stringify({
        code: 'invalid_verification_token',
        detail: 'This verification link is invalid or expired.',
        errors: null,
        request_id: '0c3054f6-558f-4264-9eb7-b48c4c693fdb',
      }),
      { status: 400, headers: { 'Content-Type': 'application/json' } },
    );
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  expect(
    await screen.findByRole('heading', { name: 'We couldn’t confirm this email' }),
  ).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Request another verification email' })).toBeTruthy();
  expect(window.location.hash).toBe('');
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

test('registration validation retains email, clears password, and writes no auth value to local storage', async () => {
  window.history.replaceState({}, '', '/register');
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=csrf-token-value',
      });
      return new Response(JSON.stringify({ csrf_token: 'csrf-token-value' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    expect(String(input)).toBe('/api/v1/auth/register/');
    expect(new Headers(init?.headers).get('X-CSRFToken')).toBe('csrf-token-value');
    return new Response(
      JSON.stringify({
        code: 'validation_error',
        detail: 'Please correct the highlighted fields.',
        errors: {
          email: ['This email is already registered.'],
          password: ['Choose a stronger password.'],
        },
        request_id: '0c3054f6-558f-4264-9eb7-b48c4c693fdb',
      }),
      { status: 400, headers: { 'Content-Type': 'application/json' } },
    );
  });
  const localStorageWrite = vi.spyOn(window.localStorage, 'setItem');
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);
  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'existing@example.com' },
  });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'weak-password' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }));

  expect(await screen.findByText('This email is already registered.')).toBeTruthy();
  expect(screen.getByLabelText('Email')).toHaveProperty('value', 'existing@example.com');
  expect(screen.getByLabelText('Password')).toHaveProperty('value', '');
  expect(localStorageWrite).not.toHaveBeenCalled();
});

test('login validation retains email, clears password, and reports field errors', async () => {
  window.history.replaceState({}, '', '/login');
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=csrf-token-value',
      });
      return new Response(JSON.stringify({ csrf_token: 'csrf-token-value' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    expect(String(input)).toBe('/api/v1/auth/login/');
    return new Response(
      JSON.stringify({
        code: 'validation_error',
        detail: 'Please correct the highlighted fields.',
        errors: {
          email: ['Enter a valid email address.'],
          password: ['Choose a stronger password.'],
        },
        request_id: '0c3054f6-558f-4264-9eb7-b48c4c693fdb',
      }),
      { status: 400, headers: { 'Content-Type': 'application/json' } },
    );
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'not-an-email' },
  });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'weak-password' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }));

  expect(await screen.findByText('Enter a valid email address.')).toBeTruthy();
  expect(screen.getByText('Choose a stronger password.')).toBeTruthy();
  expect(screen.getByLabelText('Email')).toHaveProperty('value', 'not-an-email');
  expect(screen.getByLabelText('Password')).toHaveProperty('value', '');
});

test('temporary API failures remain retryable instead of redirecting to login', async () => {
  window.history.replaceState({}, '', '/app');
  const unavailable = () =>
    new Response(
      JSON.stringify({
        code: 'service_unavailable',
        detail: 'The service is temporarily unavailable.',
        errors: null,
        request_id: '0c3054f6-558f-4264-9eb7-b48c4c693fdb',
      }),
      { status: 503, headers: { 'Content-Type': 'application/json' } },
    );
  const fetchMock = vi.fn().mockImplementation(unavailable);
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  expect(await screen.findByRole('button', { name: 'Try again' }, { timeout: 4000 })).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(3);
  expect(window.location.pathname).toBe('/app');

  fetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        id: 'c6d93bb6-8449-49b5-98cc-dc65f4ba78ab',
        email: 'verified@example.com',
        first_name: '',
        last_name: '',
        email_verified: true,
        email_verified_at: '2026-11-11T00:00:00Z',
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

  expect(await screen.findByRole('heading', { name: 'Your account' })).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledTimes(4);
});
