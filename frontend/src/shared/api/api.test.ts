import { afterEach, expect, test, vi } from 'vitest';
import { apiRequest } from './index';

afterEach(() => {
  vi.unstubAllGlobals();
});

test('API writes use same-origin credentials and send the CSRF cookie', async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=csrf-token-value',
  });
  await apiRequest('/api/v1/projects/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  const requestOptions = fetchMock.mock.calls[0]?.[1] as RequestInit;
  expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/v1/projects/');
  expect(requestOptions.credentials).toBe('same-origin');
  expect(new Headers(requestOptions.headers).get('X-CSRFToken')).toBe('csrf-token-value');
  expect(new Headers(requestOptions.headers).get('Content-Type')).toBe('application/json');
});

test('safe API requests do not send a CSRF header', async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=csrf-token-value',
  });
  await apiRequest('/api/v1/health/');

  const requestOptions = fetchMock.mock.calls[0]?.[1] as RequestInit;
  expect(requestOptions.credentials).toBe('same-origin');
  expect(new Headers(requestOptions.headers).has('X-CSRFToken')).toBe(false);
});

test('unsafe API requests bootstrap CSRF context before sending the write', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    if (String(input) === '/api/v1/auth/csrf/') {
      Object.defineProperty(document, 'cookie', {
        configurable: true,
        value: 'csrftoken=bootstrapped-csrf-token',
      });
      return new Response(JSON.stringify({ csrf_token: 'bootstrapped-csrf-token' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(null, { status: 204 });
  });
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(document, 'cookie', { configurable: true, value: '' });
  await apiRequest('/api/v1/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'user@example.com', password: 'secret-password' }),
  });

  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/v1/auth/csrf/');
  expect(fetchMock.mock.calls[1]?.[0]).toBe('/api/v1/auth/login/');
  const bootstrapOptions = fetchMock.mock.calls[0]?.[1] as RequestInit;
  const writeOptions = fetchMock.mock.calls[1]?.[1] as RequestInit;
  expect(bootstrapOptions.credentials).toBe('same-origin');
  expect(writeOptions.credentials).toBe('same-origin');
  expect(new Headers(writeOptions.headers).get('X-CSRFToken')).toBe('bootstrapped-csrf-token');
});
