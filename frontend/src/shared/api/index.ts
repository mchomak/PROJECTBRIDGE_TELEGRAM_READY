const safeMethods = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);

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

export async function apiRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const method = (init.method ?? 'GET').toUpperCase();
  const headers = new Headers(init.headers);

  if (!safeMethods.has(method)) {
    const csrfToken = readCookie('csrftoken');
    if (csrfToken) headers.set('X-CSRFToken', csrfToken);
  }

  return fetch(path, {
    ...init,
    method,
    headers,
    credentials: 'same-origin',
  });
}
