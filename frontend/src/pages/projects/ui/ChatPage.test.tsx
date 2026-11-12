import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router';
import { afterEach, expect, test, vi } from 'vitest';
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

test('shows a loading state while project chat requests are pending', async () => {
  const fetchMock = vi.fn(() => new Promise<Response>(() => undefined));
  renderChatPage(fetchMock);

  expect((await screen.findByRole('status')).textContent).toContain('Loading project chat');
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

  const heading = await screen.findByRole('heading', { name: /open this chat/ });
  expect(heading.textContent).toContain('We couldn’t open this chat');
  expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy();
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

  const list = await screen.findByRole('list', { name: 'Project messages' });
  expect(
    within(list)
      .getAllByRole('article')
      .map((item) => item.textContent),
  ).toEqual([expect.stringContaining('Later message')]);
  fireEvent.click(screen.getByRole('button', { name: 'Load older messages' }));

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

  const composer = await screen.findByRole('textbox', { name: /Message/ });
  fireEvent.change(composer, { target: { value: 'Keep this message for retry.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));

  expect((await screen.findByRole('alert')).textContent).toContain('Connection lost');
  fireEvent.click(screen.getByRole('button', { name: 'Retry message' }));
  await waitFor(() => expect(sentRequests).toHaveLength(2));
  expect(sentRequests[1]).toEqual(sentRequests[0]);
  expect(await screen.findByText('Sent')).toBeTruthy();
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

  expect(await screen.findByRole('heading', { name: 'No messages yet' })).toBeTruthy();
  expect(
    screen.getByText('This project is completed; the chat history is read only.'),
  ).toBeTruthy();
  expect(screen.queryByRole('textbox', { name: /Message/ })).toBeNull();
});
