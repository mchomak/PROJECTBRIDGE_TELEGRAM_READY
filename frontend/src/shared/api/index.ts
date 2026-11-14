import { apiErrorMessage, apiFieldErrorMessage } from '../i18n/errors';
import type { components } from './generated/schema';

const safeMethods = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);
const csrfPath = '/api/v1/auth/csrf/';

export type ApiErrorPayload = components['schemas']['ErrorEnvelope'];

export class ApiError extends Error {
  readonly status: number;
  readonly payload: ApiErrorPayload | null;

  constructor(status: number, payload: ApiErrorPayload | null) {
    super(apiErrorMessage(status, payload?.detail));
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

export function getApiFieldErrors(error: unknown): Record<string, string[]> {
  if (!(error instanceof ApiError)) return {};

  const errors = error.payload?.errors;
  if (!errors || typeof errors !== 'object' || Array.isArray(errors)) return {};

  return Object.fromEntries(
    Object.entries(errors).flatMap(([field, value]) => {
      if (typeof value === 'string') return [[field, [apiFieldErrorMessage(value)]]];
      if (Array.isArray(value)) {
        const messages = value.filter((message): message is string => typeof message === 'string');
        return messages.length ? [[field, messages.map(apiFieldErrorMessage)]] : [];
      }
      return [];
    }),
  );
}

function readCookie(name: string): string | undefined {
  const cookie = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`));

  if (!cookie) return undefined;

  const value = cookie.slice(name.length + 1);
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

let csrfBootstrap: Promise<string> | null = null;

async function getCsrfToken(): Promise<string> {
  const cookieToken = readCookie('csrftoken');
  if (cookieToken) return cookieToken;

  if (!csrfBootstrap) {
    csrfBootstrap = (async () => {
      const response = await fetch(csrfPath, {
        method: 'GET',
        credentials: 'same-origin',
      });
      const payload = (await response.json().catch(() => null)) as
        | components['schemas']['CsrfToken']
        | ApiErrorPayload
        | null;

      if (!response.ok) {
        throw new ApiError(response.status, payload as ApiErrorPayload | null);
      }

      const token =
        readCookie('csrftoken') ??
        (payload as components['schemas']['CsrfToken'] | null)?.csrf_token;
      if (!token)
        throw new Error(
          'Не удалось подтвердить безопасность запроса. Обновите страницу и попробуйте снова.',
        );
      return token;
    })();
  }

  const pendingBootstrap = csrfBootstrap;
  try {
    return await pendingBootstrap;
  } finally {
    if (csrfBootstrap === pendingBootstrap) csrfBootstrap = null;
  }
}

export async function apiRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const method = (init.method ?? 'GET').toUpperCase();
  const headers = new Headers(init.headers);

  if (!safeMethods.has(method)) {
    headers.set('X-CSRFToken', await getCsrfToken());
  }

  return fetch(path, {
    ...init,
    method,
    headers,
    credentials: 'same-origin',
  });
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiRequest(path, init);
  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, payload as ApiErrorPayload | null);
  }

  return payload as T;
}
