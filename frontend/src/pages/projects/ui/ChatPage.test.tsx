import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Link, MemoryRouter, Outlet, Route, Routes } from 'react-router';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import type { User } from '../../../entities/user';
import { ChatPage } from './ChatPage';

const projectId = 'adf680d4-d3f8-4140-b04c-b00ac64c735e';
const executorId = 'a8915ee4-1948-437a-b676-383607be7542';
const customerId = '89ab5b13-3653-4952-96f5-0fcf1de81ed7';
const olderMessageId = '5dd83716-ea0b-4e66-8879-3fb5ecbffdc9';
const newerMessageId = 'a0feab75-cd2d-4d8f-9bf4-5e890ea3a6ee';

const executor: User = {
  id: executorId,
  email: 'executor@example.com',
  first_name: 'Erin',
  last_name: 'Executor',
  email_verified: true,
  email_verified_at: '2026-11-12T00:00:00Z',
};

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  private closed = false;

  constructor(readonly url: string) {
    MockWebSocket.instances.push(this);
    queueMicrotask(() => {
      if (!this.closed) this.onopen?.(new Event('open'));
    });
  }

  close(code = 1000, reason = '') {
    if (this.closed) return;
    this.closed = true;
    this.onclose?.(new CloseEvent('close', { code, reason }));
  }

  receive(payload: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(payload) }));
  }
}

function message(overrides: Record<string, unknown> = {}) {
  return {
    id: olderMessageId,
    project_id: projectId,
    sender_id: customerId,
    content: 'Earlier message',
    message_type: 'text',
    client_message_id: 'd43a3fed-a38d-4642-9c79-9a1c2f92dbce',
    created_at: '2026-11-12T12:00:00Z',
    updated_at: null,
    ...overrides,
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function renderChatPage(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=chat-page-test-token',
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/projects/${projectId}/chat`]}>
        <Routes>
          <Route element={<Outlet context={executor} />}>
            <Route path="/app/projects/:projectId/chat" element={<ChatPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function chatFetch(
  onSend?: (payload: { client_message_id: string; content: string }) => Response,
  history: { results: ReturnType<typeof message>[]; next?: string | null } = {
    results: [],
    next: null,
  },
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (url === `/api/v1/projects/${projectId}/`) {
      return jsonResponse({
        id: projectId,
        name: 'Telegram delivery bot',
        description: 'A shared project',
        project_type: 'telegram_bot',
        status: 'active',
        created_at: '2026-11-12T00:00:00Z',
        updated_at: '2026-11-12T00:00:00Z',
        completed_at: null,
        archived_at: null,
      });
    }
    if (url === `/api/v1/projects/${projectId}/members/`) {
      return jsonResponse([
        {
          id: executorId,
          user_id: executorId,
          role: 'executor',
          joined_at: '2026-11-12T00:00:00Z',
          first_name: 'Erin',
          last_name: 'Executor',
        },
        {
          id: customerId,
          user_id: customerId,
          role: 'customer',
          joined_at: '2026-11-12T00:00:00Z',
          first_name: 'Casey',
          last_name: 'Customer',
        },
      ]);
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/messages/`) && method === 'GET') {
      const query = new URL(url, 'http://localhost').searchParams;
      if (query.get('cursor') === 'older') {
        return jsonResponse({
          next: null,
          previous: null,
          results: [message()],
        });
      }
      return jsonResponse({
        next: history.next ?? null,
        previous: null,
        results: history.results,
      });
    }
    if (url === `/api/v1/projects/${projectId}/messages/` && method === 'POST') {
      const payload = JSON.parse(String(init?.body)) as {
        client_message_id: string;
        content: string;
      };
      return (
        onSend?.(payload) ??
        jsonResponse(
          message({
            id: newerMessageId,
            sender_id: executorId,
            client_message_id: payload.client_message_id,
            content: payload.content,
            created_at: '2026-11-12T12:02:00Z',
          }),
          201,
        )
      );
    }
    throw new Error(`Unexpected request: ${method} ${url}`);
  });
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

beforeEach(() => {
  MockWebSocket.instances = [];
  vi.stubGlobal('WebSocket', MockWebSocket);
});

test('shows a loading state while project chat requests are pending', async () => {
  const fetchMock = vi.fn(() => new Promise<Response>(() => undefined));
  renderChatPage(fetchMock);

  expect((await screen.findByRole('status')).textContent).toContain('Загрузка чата проекта');
});

test('shows a recoverable error state when REST history is unavailable', async () => {
  const baseFetch = chatFetch();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input).includes('/messages/')) {
      return jsonResponse(
        { code: 'internal_error', detail: 'History unavailable', errors: null, request_id: 'test' },
        500,
      );
    }
    return baseFetch(input, init);
  });
  renderChatPage(fetchMock);

  const heading = await screen.findByRole('heading', { name: /открыть чат/ });
  expect(heading.textContent).toContain('Не удалось открыть чат');
  expect(screen.getByRole('button', { name: 'Попробовать снова' })).toBeTruthy();
});

test('renders REST history chronologically and loads an older cursor page', async () => {
  const fetchMock = chatFetch(undefined, {
    results: [
      message({
        id: newerMessageId,
        content: 'Later message',
        created_at: '2026-11-12T12:01:00Z',
      }),
    ],
    next: 'http://testserver/api/v1/projects/messages/?cursor=older',
  });
  renderChatPage(fetchMock);

  const list = await screen.findByRole('list', { name: 'Сообщения проекта' });
  expect(
    within(list)
      .getAllByRole('article')
      .map((item) => item.textContent),
  ).toEqual([expect.stringContaining('Later message')]);
  fireEvent.click(screen.getByRole('button', { name: 'Загрузить предыдущие сообщения' }));

  expect(await within(list).findByText('Earlier message')).toBeTruthy();
  const renderedMessages = within(list).getAllByRole('article');
  expect(renderedMessages[0].textContent).toContain('Earlier message');
  expect(renderedMessages[1].textContent).toContain('Later message');
  expect(fetchMock.mock.calls.map(([input]) => String(input))).toContain(
    `/api/v1/projects/${projectId}/messages/?page_size=50&cursor=older`,
  );
});

test('keeps a failed draft and retries with the original client ID and content', async () => {
  const sentRequests: Array<{ client_message_id: string; content: string }> = [];
  const fetchMock = chatFetch((payload) => {
    sentRequests.push(payload);
    if (sentRequests.length === 1) {
      return jsonResponse(
        { code: 'internal_error', detail: 'Connection lost', errors: null, request_id: 'test' },
        500,
      );
    }
    return jsonResponse(
      message({
        id: newerMessageId,
        sender_id: executorId,
        client_message_id: payload.client_message_id,
        content: payload.content,
        created_at: '2026-11-12T12:02:00Z',
      }),
      201,
    );
  });
  renderChatPage(fetchMock);

  const composer = await screen.findByRole('textbox', { name: /Сообщение/ });
  fireEvent.change(composer, { target: { value: 'Keep this message for retry.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Отправить сообщение' }));

  expect((await screen.findByRole('alert')).textContent).toContain('Не удалось выполнить запрос');
  fireEvent.click(screen.getByRole('button', { name: 'Повторить отправку' }));
  await waitFor(() => expect(sentRequests).toHaveLength(2));
  expect(sentRequests[1]).toEqual(sentRequests[0]);
  expect(await screen.findByText('Отправлено')).toBeTruthy();
});

test('preserves compose text after a REST rate limit and can retry the message', async () => {
  const sentRequests: Array<{ client_message_id: string; content: string }> = [];
  const fetchMock = chatFetch((payload) => {
    sentRequests.push(payload);
    if (sentRequests.length === 1) {
      return jsonResponse(
        {
          code: 'throttled',
          detail: 'Chat send rate limit exceeded.',
          errors: null,
          request_id: 'test',
        },
        429,
      );
    }
    return jsonResponse(
      message({
        id: newerMessageId,
        sender_id: executorId,
        client_message_id: payload.client_message_id,
        content: payload.content,
        created_at: '2026-11-12T12:02:00Z',
      }),
      201,
    );
  });
  renderChatPage(fetchMock);

  const composer = (await screen.findByRole('textbox', {
    name: /Сообщение/,
  })) as HTMLTextAreaElement;
  const content = 'Keep this message while the chat limit resets.';
  fireEvent.change(composer, { target: { value: content } });
  fireEvent.click(screen.getByRole('button', { name: 'Отправить сообщение' }));

  expect((await screen.findByRole('alert')).textContent).toContain('Слишком много запросов');
  expect(composer.value).toBe(content);
  fireEvent.click(screen.getByRole('button', { name: 'Повторить отправку' }));
  await waitFor(() => expect(sentRequests).toHaveLength(2));
  expect(sentRequests[1]).toEqual(sentRequests[0]);
  await waitFor(() => expect(composer.value).toBe(''));
});

test('deduplicates WebSocket events and reloads REST history after reconnect', async () => {
  const missedMessage = message({
    id: newerMessageId,
    content: 'Recovered after reconnect.',
    created_at: '2026-11-12T12:03:00Z',
  });
  const liveMessage = message({
    id: 'ebdbf186-f5c6-45e6-87b1-4767a7b53b83',
    content: 'Delivered live.',
    created_at: '2026-11-12T12:02:00Z',
  });
  let includeHistory = false;
  let historyCalls = 0;
  const baseFetch = chatFetch();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (
      url.startsWith(`/api/v1/projects/${projectId}/messages/`) &&
      (init?.method ?? 'GET') === 'GET'
    ) {
      historyCalls += 1;
      return jsonResponse({
        next: null,
        previous: null,
        results: includeHistory ? [liveMessage, missedMessage] : [],
      });
    }
    return baseFetch(input, init);
  });
  renderChatPage(fetchMock);

  expect(await screen.findByRole('heading', { name: 'Сообщений пока нет' })).toBeTruthy();
  await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
  const firstSocket = MockWebSocket.instances[0];
  expect(firstSocket.url).toBe(`ws://localhost:3000/ws/v1/projects/${projectId}/chat/`);

  act(() => firstSocket.receive({ type: 'message.created', message: liveMessage }));
  const list = await screen.findByRole('list', { name: 'Сообщения проекта' });
  expect(await within(list).findByText('Delivered live.')).toBeTruthy();
  act(() => firstSocket.receive({ type: 'message.created', message: liveMessage }));
  expect(within(list).getAllByRole('article')).toHaveLength(1);

  const composer = (await screen.findByRole('textbox', {
    name: /Сообщение/,
  })) as HTMLTextAreaElement;
  fireEvent.change(composer, { target: { value: 'Keep composing through reconnect.' } });
  includeHistory = true;
  act(() => firstSocket.close(1006, 'Network disconnected'));

  await waitFor(() => expect(MockWebSocket.instances).toHaveLength(2), { timeout: 2000 });
  expect(await within(list).findByText('Recovered after reconnect.')).toBeTruthy();
  await waitFor(() => expect(historyCalls).toBeGreaterThan(1));
  expect(within(list).getAllByRole('article')).toHaveLength(2);
  expect(composer.value).toBe('Keep composing through reconnect.');
});

test('shows an empty message state and disables sending for a completed project', async () => {
  const fetchMock = chatFetch();
  fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === `/api/v1/projects/${projectId}/`) {
      return jsonResponse({
        id: projectId,
        name: 'Telegram delivery bot',
        description: 'A shared project',
        project_type: 'telegram_bot',
        status: 'completed',
        created_at: '2026-11-12T00:00:00Z',
        updated_at: '2026-11-12T00:00:00Z',
        completed_at: '2026-11-12T12:00:00Z',
        archived_at: null,
      });
    }
    return chatFetch()(input, init);
  });
  renderChatPage(fetchMock);

  expect(await screen.findByRole('heading', { name: 'Сообщений пока нет' })).toBeTruthy();
  expect(
    screen.getByText('Статус проекта: Завершён. История чата доступна только для чтения.'),
  ).toBeTruthy();
  expect(screen.queryByRole('textbox', { name: /Сообщение/ })).toBeNull();
});

test('keeps a WebSocket-confirmed send as sent when the REST response fails', async () => {
  let failRequest: ((response: Response) => void) | undefined;
  let submitted: { client_message_id: string; content: string } | undefined;
  const baseFetch = chatFetch();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input).endsWith('/messages/') && init?.method === 'POST') {
      submitted = JSON.parse(String(init.body)) as { client_message_id: string; content: string };
      return new Promise<Response>((resolve) => {
        failRequest = resolve;
      });
    }
    return baseFetch(input, init);
  });
  renderChatPage(fetchMock);
  const composer = await screen.findByRole('textbox', { name: /Сообщение/ });
  fireEvent.change(composer, { target: { value: 'Already delivered' } });
  fireEvent.click(screen.getByRole('button', { name: 'Отправить сообщение' }));
  await waitFor(() => expect(submitted).toBeDefined());
  act(() =>
    MockWebSocket.instances[0].receive({
      type: 'message.created',
      message: message({
        id: newerMessageId,
        sender_id: executorId,
        content: 'Already delivered',
        client_message_id: submitted?.client_message_id,
      }),
    }),
  );
  act(() => failRequest?.(jsonResponse({ detail: 'Network error' }, 500)));
  await waitFor(() => expect(screen.getByText('Отправлено')).toBeTruthy());
  expect((composer as HTMLTextAreaElement).value).toBe('');
  expect(screen.queryByRole('button', { name: 'Повторить отправку' })).toBeNull();
});

test('keeps distinct messages when participants use the same client message ID', async () => {
  const clientId = 'd43a3fed-a38d-4642-9c79-9a1c2f92dbce';
  const fetchMock = chatFetch(undefined, {
    results: [
      message({ sender_id: executorId, content: 'My message', client_message_id: clientId }),
    ],
  });
  renderChatPage(fetchMock);
  expect(await screen.findByText('My message')).toBeTruthy();
  await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
  act(() =>
    MockWebSocket.instances[0].receive({
      type: 'message.created',
      message: message({
        id: newerMessageId,
        sender_id: customerId,
        content: 'Customer message',
        client_message_id: clientId,
      }),
    }),
  );
  expect(await screen.findByText('Customer message')).toBeTruthy();
  expect(screen.getByText('My message')).toBeTruthy();
});

test('does not carry live messages or draft text into another project chat', async () => {
  const otherProjectId = '9b66d97b-73c7-48db-8a99-a6b56395177d';
  const baseFetch = chatFetch();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === `/api/v1/projects/${otherProjectId}/`) {
      return jsonResponse({
        id: otherProjectId,
        name: 'Other project',
        project_type: 'other',
        status: 'active',
      });
    }
    return baseFetch(url.replace(otherProjectId, projectId), init);
  });
  vi.stubGlobal('fetch', fetchMock);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/projects/${projectId}/chat`]}>
        <Link to={`/app/projects/${otherProjectId}/chat`}>Other chat</Link>
        <Routes>
          <Route element={<Outlet context={executor} />}>
            <Route path="/app/projects/:projectId/chat" element={<ChatPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  const composer = await screen.findByRole('textbox', { name: /Сообщение/ });
  fireEvent.change(composer, { target: { value: 'Private draft' } });
  await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
  act(() =>
    MockWebSocket.instances[0].receive({
      type: 'message.created',
      message: message({ content: 'Previous project message' }),
    }),
  );
  expect(await screen.findByText('Previous project message')).toBeTruthy();
  fireEvent.click(screen.getByRole('link', { name: 'Other chat' }));
  expect(await screen.findByRole('heading', { name: 'Other project' })).toBeTruthy();
  expect(screen.queryByText('Previous project message')).toBeNull();
  expect((screen.getByRole('textbox', { name: /Сообщение/ }) as HTMLTextAreaElement).value).toBe(
    '',
  );
});

test('REST history confirms a failed send and preserves a subsequently edited draft', async () => {
  let saved: ReturnType<typeof message> | undefined;
  const baseFetch = chatFetch();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith('/messages/') && init?.method === 'POST') {
      const payload = JSON.parse(String(init.body)) as {
        client_message_id: string;
        content: string;
      };
      saved = message({ id: newerMessageId, sender_id: executorId, ...payload });
      return jsonResponse({ detail: 'Response lost' }, 500);
    }
    if (url.includes('/messages/?') && saved) {
      return jsonResponse({ next: null, previous: null, results: [saved] });
    }
    return baseFetch(input, init);
  });
  renderChatPage(fetchMock);
  const composer = (await screen.findByRole('textbox', {
    name: /Сообщение/,
  })) as HTMLTextAreaElement;
  fireEvent.change(composer, { target: { value: 'Saved but response lost' } });
  fireEvent.click(screen.getByRole('button', { name: 'Отправить сообщение' }));
  expect(await screen.findByRole('alert')).toBeTruthy();
  fireEvent.change(composer, { target: { value: 'A new draft' } });
  act(() => MockWebSocket.instances[0].close(1006));
  await waitFor(() => expect(MockWebSocket.instances).toHaveLength(2));
  await waitFor(() =>
    expect(screen.queryByRole('button', { name: 'Повторить отправку' })).toBeNull(),
  );
  expect(screen.getByText('Отправлено')).toBeTruthy();
  expect(composer.value).toBe('A new draft');
});
