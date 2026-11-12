import { afterEach, expect, test, vi } from 'vitest';
import { createProjectMessage, getProjectMessages } from './chatApi';

const projectId = 'adf680d4-d3f8-4140-b04c-b00ac64c735e';
const messageId = '9ed59d0a-4e10-4225-9bd7-33254fc03799';
const clientMessageId = '6139bb2d-f172-44df-bcfb-3846cb5beb4f';

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test('history requests a cursor page with the requested limit', async () => {
  const fetchMock = vi.fn(async () =>
    jsonResponse({ count: 2, next: null, previous: null, results: [] }),
  );
  vi.stubGlobal('fetch', fetchMock);

  await getProjectMessages(projectId, 'signed cursor', 25);

  expect(fetchMock).toHaveBeenCalledWith(
    `/api/v1/projects/${projectId}/messages/?page_size=25&cursor=signed+cursor`,
    expect.objectContaining({ method: 'GET', credentials: 'same-origin' }),
  );
});

test('sending a message posts the client id and text using the shared API client', async () => {
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=chat-csrf-token',
  });
  const message = {
    id: messageId,
    project_id: projectId,
    sender_id: 'a8915ee4-1948-437a-b676-383607be7542',
    content: 'The plan is ready.',
    message_type: 'text',
    client_message_id: clientMessageId,
    created_at: '2026-11-12T12:00:00Z',
    updated_at: null,
  };
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
    jsonResponse(message),
  );
  vi.stubGlobal('fetch', fetchMock);

  await createProjectMessage(projectId, {
    client_message_id: clientMessageId,
    content: 'The plan is ready.',
  });

  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, init] = fetchMock.mock.calls[0];
  if (!init) throw new Error('Expected request options for the message send.');
  expect(url).toBe(`/api/v1/projects/${projectId}/messages/`);
  expect(init).toMatchObject({
    method: 'POST',
    credentials: 'same-origin',
    body: JSON.stringify({
      client_message_id: clientMessageId,
      content: 'The plan is ready.',
    }),
  });
  const headers = new Headers(init.headers);
  expect(headers.get('Content-Type')).toBe('application/json');
  expect(headers.get('X-CSRFToken')).toBe('chat-csrf-token');
});
