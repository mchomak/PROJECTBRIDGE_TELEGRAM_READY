import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../../../app/App';

const verifiedUser = {
  id: 'd52c7331-4f61-4468-9a4c-b4f4b28bfcf5',
  email: 'customer@example.com',
  first_name: '',
  last_name: '',
  email_verified: true,
  email_verified_at: '2026-11-12T00:00:00Z',
};

const preview = {
  project_name: 'Customer website',
  email_hint: 'c***@example.com',
  expires_at: '2026-11-19T00:00:00Z',
  status: 'pending',
};

function setCsrfCookie() {
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=csrf-token-value',
  });
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function errorResponse(status: number, code: string, detail: string) {
  return jsonResponse({ code, detail, errors: null, request_id: 'request-id' }, status);
}

afterEach(() => {
  window.history.replaceState({}, '', '/');
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test('shows a loading state while invitation preview is pending', async () => {
  window.history.replaceState({}, '', '/invite/#token=email-link-secret');
  let finishPreview: ((response: Response) => void) | undefined;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') {
      setCsrfCookie();
      return jsonResponse({ csrf_token: 'csrf-token-value' });
    }
    if (path === '/api/v1/invitations/preview/') {
      return new Promise<Response>((resolve) => {
        finishPreview = resolve;
      });
    }
    if (path === '/api/v1/auth/me/') {
      return errorResponse(401, 'not_authenticated', 'Authentication required.');
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<App />);

  expect(await screen.findByRole('status')).toBeTruthy();
  await waitFor(() => expect(finishPreview).toBeTypeOf('function'));
  finishPreview?.(jsonResponse(preview));
  expect(
    await screen.findByRole('heading', { name: 'You’re invited to Customer website' }),
  ).toBeTruthy();
});

test('invitation preview removes the fragment and sends the token only in the preview body', async () => {
  window.history.replaceState({}, '', '/invite/#token=email-link-secret');
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') {
      setCsrfCookie();
      return jsonResponse({ csrf_token: 'csrf-token-value' });
    }
    if (path === '/api/v1/invitations/preview/') {
      expect(window.location.hash).toBe('');
      expect(init?.method).toBe('POST');
      expect(JSON.parse(String(init?.body))).toEqual({ token: 'email-link-secret' });
      expect(path).not.toContain('email-link-secret');
      return jsonResponse(preview);
    }
    if (path === '/api/v1/auth/me/') {
      return errorResponse(401, 'not_authenticated', 'Authentication required.');
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  const localStorageWrite = vi.spyOn(window.localStorage, 'setItem');
  vi.stubGlobal('fetch', fetchMock);

  render(<App />);

  expect(
    await screen.findByRole('heading', { name: 'You’re invited to Customer website' }),
  ).toBeTruthy();
  expect(await screen.findByLabelText('Email')).toBeTruthy();
  expect(screen.getByLabelText('Password')).toBeTruthy();
  expect(window.location.pathname).toBe('/invite/');
  expect(window.location.hash).toBe('');
  expect(localStorageWrite).not.toHaveBeenCalled();
});

test('invited customer can log in, accept, and enter the customer project', async () => {
  window.history.replaceState({}, '', '/invite/#token=email-link-secret');
  const projectId = 'c8aaf2dd-ec82-4c7b-9d4c-0f84d6c45c36';
  let isAuthenticated = false;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') {
      setCsrfCookie();
      return jsonResponse({ csrf_token: 'csrf-token-value' });
    }
    if (path === '/api/v1/invitations/preview/') return jsonResponse(preview);
    if (path === '/api/v1/auth/me/') {
      return isAuthenticated
        ? jsonResponse(verifiedUser)
        : errorResponse(401, 'not_authenticated', 'Authentication required.');
    }
    if (path === '/api/v1/auth/login/') {
      expect(JSON.parse(String(init?.body))).toEqual({
        email: 'customer@example.com',
        password: 'correct-horse-battery',
      });
      isAuthenticated = true;
      return jsonResponse(verifiedUser);
    }
    if (path === '/api/v1/invitations/accept/') {
      expect(JSON.parse(String(init?.body))).toEqual({ token: 'email-link-secret' });
      return jsonResponse({
        invitation_id: 'f56b6d31-633f-4f5a-96d1-4e5deaa1d7cb',
        project_id: projectId,
        status: 'accepted',
      });
    }
    if (path === `/api/v1/projects/${projectId}/`) {
      return jsonResponse({
        id: projectId,
        name: 'Accepted customer project',
        description: 'Shared project details',
        project_type: 'website',
        status: 'active',
        created_at: '2026-11-12T00:00:00Z',
        updated_at: '2026-11-12T00:00:00Z',
        completed_at: null,
        archived_at: null,
      });
    }
    if (path === `/api/v1/projects/${projectId}/members/`) {
      return jsonResponse([
        {
          id: verifiedUser.id,
          user_id: verifiedUser.id,
          role: 'customer',
          joined_at: '2026-11-12T00:00:00Z',
          first_name: '',
          last_name: '',
        },
      ]);
    }
    if (path === `/api/v1/projects/${projectId}/passport/`) {
      return jsonResponse({
        id: '1ef31b46-3a5c-4e22-a356-2cc32f6d5ce2',
        project_id: projectId,
        goal: '',
        target_audience: '',
        expected_result: '',
        functional_scope: [],
        integrations: {},
        constraints: [],
        deadline: null,
        budget_min: null,
        budget_max: null,
        currency: null,
        additional_data: {},
        version: 1,
        created_at: '2026-11-12T00:00:00Z',
        updated_at: '2026-11-12T00:00:00Z',
      });
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<App />);

  await screen.findByRole('heading', { name: 'You’re invited to Customer website' });
  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'customer@example.com' },
  });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'correct-horse-battery' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Log in' }));

  fireEvent.click(await screen.findByRole('button', { name: 'Accept invitation' }));

  expect(await screen.findByRole('heading', { name: 'Accepted customer project' })).toBeTruthy();
  expect(window.location.pathname).toBe(`/app/projects/${projectId}`);
  expect(
    fetchMock.mock.calls.some(([input]) => String(input) === `/api/v1/projects/${projectId}/`),
  ).toBe(true);
  expect(
    fetchMock.mock.calls.some(([input]) => String(input) === '/api/v1/invitations/accept/'),
  ).toBe(true);
});

test('invited customer can register and sees the verification handoff', async () => {
  window.history.replaceState({}, '', '/invite/#token=email-link-secret');
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') {
      setCsrfCookie();
      return jsonResponse({ csrf_token: 'csrf-token-value' });
    }
    if (path === '/api/v1/invitations/preview/') return jsonResponse(preview);
    if (path === '/api/v1/auth/me/') {
      return errorResponse(401, 'not_authenticated', 'Authentication required.');
    }
    if (path === '/api/v1/auth/register/') {
      expect(JSON.parse(String(init?.body))).toEqual({
        email: 'customer@example.com',
        password: 'strong-password-value',
      });
      return jsonResponse({ ...verifiedUser, email_verified: false, email_verified_at: null }, 201);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<App />);

  await screen.findByRole('heading', { name: 'You’re invited to Customer website' });
  fireEvent.click(screen.getByRole('button', { name: 'Create an account' }));
  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: 'customer@example.com' },
  });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'strong-password-value' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }));

  expect(await screen.findByText(/verification email/i)).toBeTruthy();
  expect(window.location.hash).toBe('');
});

test.each([
  [404, 'not_found', 'This invitation link is invalid'],
  [410, 'invitation_expired', 'This invitation has expired'],
  [410, 'invitation_revoked', 'This invitation was revoked'],
  [409, 'project_completed', 'This project is complete'],
  [409, 'project_archived', 'This project is archived'],
  [429, 'throttled', 'Too many invitation checks'],
] as const)('shows a safe invitation state for %s %s', async (status, code, title) => {
  window.history.replaceState({}, '', '/invite/#token=email-link-secret');
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') {
      setCsrfCookie();
      return jsonResponse({ csrf_token: 'csrf-token-value' });
    }
    if (path === '/api/v1/invitations/preview/') {
      return errorResponse(status, code, 'Private project name must remain hidden.');
    }
    if (path === '/api/v1/auth/me/') {
      return errorResponse(401, 'not_authenticated', 'Authentication required.');
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<App />);

  expect(await screen.findByRole('heading', { name: title })).toBeTruthy();
  expect(screen.queryByText('Private project name must remain hidden.')).toBeNull();
});

test('a verified user with a different email sees a recoverable mismatch state', async () => {
  window.history.replaceState({}, '', '/invite/#token=email-link-secret');
  const otherUser = { ...verifiedUser, email: 'other@example.com' };
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') {
      setCsrfCookie();
      return jsonResponse({ csrf_token: 'csrf-token-value' });
    }
    if (path === '/api/v1/invitations/preview/') return jsonResponse(preview);
    if (path === '/api/v1/auth/me/') return jsonResponse(otherUser);
    if (path === '/api/v1/invitations/accept/') {
      return errorResponse(403, 'email_mismatch', 'Sign in with the invited email.');
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<App />);

  await screen.findByRole('heading', { name: 'You’re invited to Customer website' });
  fireEvent.click(await screen.findByRole('button', { name: 'Accept invitation' }));

  expect(await screen.findByText(/invitation belongs to c\*\*\*@example\.com/i)).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Use another account' })).toBeTruthy();
});

test('acceptance expiry shows the expired state and removes the accept action', async () => {
  window.history.replaceState({}, '', '/invite/#token=email-link-secret');
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') {
      setCsrfCookie();
      return jsonResponse({ csrf_token: 'csrf-token-value' });
    }
    if (path === '/api/v1/invitations/preview/') return jsonResponse(preview);
    if (path === '/api/v1/auth/me/') return jsonResponse(verifiedUser);
    if (path === '/api/v1/invitations/accept/') {
      return errorResponse(410, 'invitation_expired', 'This invitation has expired.');
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<App />);

  await screen.findByRole('heading', { name: 'You’re invited to Customer website' });
  fireEvent.click(await screen.findByRole('button', { name: 'Accept invitation' }));

  expect(
    await screen.findByText('Ask the project executor to send a new invitation.'),
  ).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Accept invitation' })).toBeNull();
});

test('unverified invited user can refresh the account state after email verification', async () => {
  window.history.replaceState({}, '', '/invite/#token=email-link-secret');
  const unverifiedUser = { ...verifiedUser, email_verified: false, email_verified_at: null };
  let accountReads = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') {
      setCsrfCookie();
      return jsonResponse({ csrf_token: 'csrf-token-value' });
    }
    if (path === '/api/v1/invitations/preview/') return jsonResponse(preview);
    if (path === '/api/v1/auth/me/') {
      accountReads += 1;
      return jsonResponse(accountReads === 1 ? unverifiedUser : verifiedUser);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  render(<App />);

  expect(
    await screen.findByRole('heading', { name: 'Verify your email to continue' }),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'I’ve verified my email' }));

  expect(await screen.findByRole('button', { name: 'Accept invitation' })).toBeTruthy();
});
