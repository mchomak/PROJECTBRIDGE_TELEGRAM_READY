import { afterEach, expect, test, vi } from 'vitest';
import { ApiError, apiJson, apiRequest } from './index';

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

test('a missing CSRF token produces a localized error and does not send the write', async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(document, 'cookie', { configurable: true, value: '' });

  await expect(apiRequest('/api/v1/projects/', { method: 'POST' })).rejects.toThrow(
    'Не удалось подтвердить безопасность запроса. Обновите страницу и попробуйте снова.',
  );
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/v1/auth/csrf/');
});

test('API errors retain the response payload while displaying a translated message', async () => {
  const payload = {
    code: 'request_failed',
    detail: 'The document exceeds the 20 MiB upload limit.',
    errors: null,
    request_id: 'id',
  };
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 413 })),
  );
  const error: unknown = await apiJson('/api/v1/documents/').catch((caught: unknown) => caught);
  expect(error).toBeInstanceOf(ApiError);
  if (!(error instanceof ApiError)) throw new Error('Expected an ApiError');
  expect(error.message).toBe('Размер документа превышает допустимые 20 МиБ.');
  expect(error.payload).toEqual(payload);
});
