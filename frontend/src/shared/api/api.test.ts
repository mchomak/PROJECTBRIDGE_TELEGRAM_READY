import { afterEach, expect, test, vi } from 'vitest';

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
  const apiModule = await import('./index').catch(() => null);
  expect(apiModule).not.toBeNull();
  if (!apiModule) return;

  await apiModule.apiRequest('/api/v1/projects/', {
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
  const apiModule = await import('./index').catch(() => null);
  expect(apiModule).not.toBeNull();
  if (!apiModule) return;

  await apiModule.apiRequest('/api/v1/health/');

  const requestOptions = fetchMock.mock.calls[0]?.[1] as RequestInit;
  expect(requestOptions.credentials).toBe('same-origin');
  expect(new Headers(requestOptions.headers).has('X-CSRFToken')).toBe(false);
});
