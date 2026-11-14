import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router';
import type { User } from '../../../entities/user';
import { ProjectStatePage } from './ProjectStatePage';

const projectId = '1e3ae97f-6517-4eac-b81f-b94d34c73f2e';
const executorId = 'b2e3d4f1-65d0-463c-ac4f-68674cf57822';
const customerId = '497a8eb7-fb6a-405b-a8ce-6d8c2d87231d';

const executor: User = {
  id: executorId,
  email: 'executor@example.com',
  first_name: 'Erin',
  last_name: 'Executor',
  email_verified: true,
  email_verified_at: '2026-11-12T00:00:00Z',
};

const customer: User = {
  id: customerId,
  email: 'customer@example.com',
  first_name: 'Casey',
  last_name: 'Customer',
  email_verified: true,
  email_verified_at: '2026-11-12T00:00:00Z',
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function stage(id: string, name: string, dueDate: string | null = null) {
  return {
    id,
    project_id: projectId,
    name,
    description: 'Agree the initial delivery plan.',
    position: 0,
    status: 'planned',
    start_date: null,
    due_date: dueDate,
    created_by_id: executorId,
    created_at: '2026-11-12T00:00:00Z',
    updated_at: '2026-11-12T00:00:00Z',
  };
}

type StateTestConflict = {
  id: string;
  [key: string]: unknown;
};

function renderPage(fetchMock: ReturnType<typeof vi.fn>, pageUser: User) {
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=project-state-test-token',
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/projects/${projectId}/state`]}>
        <Routes>
          <Route element={<Outlet context={pageUser} />}>
            <Route path="/app/projects/:projectId/state" element={<ProjectStatePage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stateFetch(
  userId: string,
  initial?: { stages?: ReturnType<typeof stage>[]; conflicts?: StateTestConflict[] },
) {
  const records = initial?.stages ?? [
    stage('d6d12757-205c-4540-a9fd-5712fb2b3530', 'Discovery', '2026-12-01'),
  ];
  const conflictRecords = initial?.conflicts ?? [];
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
        created_by_id: executorId,
        created_at: '2026-11-12T00:00:00Z',
        updated_at: '2026-11-12T00:00:00Z',
      });
    }
    if (url === `/api/v1/projects/${projectId}/members/`) {
      return jsonResponse([
        {
          id: 'member-executor',
          user_id: executorId,
          role: 'executor',
          joined_at: '2026-11-12T00:00:00Z',
          first_name: 'Erin',
          last_name: 'Executor',
        },
        {
          id: 'member-customer',
          user_id: customerId,
          role: 'customer',
          joined_at: '2026-11-12T00:00:00Z',
          first_name: 'Casey',
          last_name: 'Customer',
        },
      ]);
    }
    if (url === `/api/v1/projects/${projectId}/state/`) {
      return jsonResponse({
        project_id: projectId,
        counts: {
          stages: records.length,
          requirements: 0,
          tasks: 0,
          open_questions: 0,
          conflicts: conflictRecords.length,
        },
        collections: {
          stages: `/api/v1/projects/${projectId}/stages/`,
          requirements: `/api/v1/projects/${projectId}/requirements/`,
          tasks: `/api/v1/projects/${projectId}/tasks/`,
          open_questions: `/api/v1/projects/${projectId}/open-questions/`,
          conflicts: `/api/v1/projects/${projectId}/conflicts/`,
          evidence_options: `/api/v1/projects/${projectId}/evidence-options/`,
        },
      });
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/stages/`) && method === 'POST') {
      const payload = JSON.parse(String(init?.body)) as { name: string };
      const created = stage('1594bd90-c810-4af1-85e5-23c36353f0c1', payload.name);
      records.push(created);
      return jsonResponse(created, 201);
    }
    if (url.startsWith('/api/v1/stages/') && method === 'PATCH') {
      const record = records.find(({ id }) => url === `/api/v1/stages/${id}/`);
      if (record) {
        Object.assign(record, JSON.parse(String(init?.body)) as object);
        return jsonResponse(record);
      }
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/stages/`)) {
      return jsonResponse({ count: records.length, next: null, previous: null, results: records });
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/requirements/`)) {
      return jsonResponse({ count: 0, next: null, previous: null, results: [] });
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/tasks/`)) {
      return jsonResponse({ count: 0, next: null, previous: null, results: [] });
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/open-questions/`)) {
      return jsonResponse({ count: 0, next: null, previous: null, results: [] });
    }
    if (url.startsWith('/api/v1/conflicts/') && method === 'PATCH') {
      const conflict = conflictRecords.find(({ id }) => url === `/api/v1/conflicts/${id}/`);
      if (conflict) {
        Object.assign(conflict, JSON.parse(String(init?.body)) as object);
        return jsonResponse(conflict);
      }
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/conflicts/`)) {
      return jsonResponse({
        count: conflictRecords.length,
        next: null,
        previous: null,
        results: conflictRecords,
      });
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/evidence-options/`)) {
      return jsonResponse({ count: 0, next: null, previous: null, results: [] });
    }
    return jsonResponse(
      { code: 'not_found', detail: `Unhandled test URL for ${userId}`, errors: null },
      404,
    );
  });
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test('executor can add a stage with a due date and sees its status', async () => {
  const fetchMock = stateFetch(executorId);
  renderPage(fetchMock, executor);

  expect(await screen.findByRole('heading', { name: 'Discovery' })).toBeTruthy();
  expect(screen.getByText(/Срок: 2026-12-01/)).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Изменить этап' })).toBeTruthy();
  expect(screen.queryByText(/percentage|gantt/i)).toBeNull();

  fireEvent.click(screen.getByText('Добавить этап'));
  fireEvent.change(screen.getByLabelText('Название этапа'), { target: { value: 'Build' } });
  fireEvent.click(screen.getByRole('button', { name: 'Создать этап' }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/projects/${projectId}/stages/`,
      expect.objectContaining({ method: 'POST' }),
    );
  });
  expect(await screen.findByRole('heading', { name: 'Build' })).toBeTruthy();
});

test('customer reads shared Project State without create or edit controls', async () => {
  const fetchMock = stateFetch(customerId);
  renderPage(fetchMock, customer);

  expect(await screen.findByRole('heading', { name: 'Discovery' })).toBeTruthy();
  expect(screen.getByText('Запланирован')).toBeTruthy();
  expect(screen.getByText(/Срок: 2026-12-01/)).toBeTruthy();
  expect(screen.getByText('Исполнитель ещё не добавил требования.')).toBeTruthy();
  expect(screen.queryByText('Добавить этап')).toBeNull();
  expect(screen.queryByRole('button', { name: 'Изменить этап' })).toBeNull();
  expect(fetchMock).not.toHaveBeenCalledWith(
    expect.stringContaining('/evidence-options/'),
    expect.anything(),
  );
});

test('customer sees a clear empty state when no shared state has been added', async () => {
  const fetchMock = stateFetch(customerId, { stages: [], conflicts: [] });
  renderPage(fetchMock, customer);

  expect(await screen.findByText('Исполнитель ещё не добавил этапы.')).toBeTruthy();
  expect(screen.queryByText(/percentage|gantt/i)).toBeNull();
  expect(screen.queryByText('Add the first stages to the shared project plan.')).toBeNull();
});

test('customer can retry after a Project State load error', async () => {
  const stateUrl = `/api/v1/projects/${projectId}/state/`;
  const fallbackFetch = stateFetch(customerId);
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === stateUrl) {
      return Promise.resolve(
        jsonResponse({ code: 'server_error', detail: 'Try again later.' }, 500),
      );
    }
    return fallbackFetch(input, init);
  });
  renderPage(fetchMock, customer);

  expect(
    await screen.findByRole('heading', { name: 'Не удалось загрузить состояние проекта' }),
  ).toBeTruthy();
  expect(screen.getByText('Не удалось выполнить запрос. Попробуйте ещё раз.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Попробовать снова' }));

  await waitFor(() => {
    expect(fetchMock.mock.calls.filter(([url]) => String(url) === stateUrl).length).toBeGreaterThan(
      1,
    );
  });
  expect(
    await screen.findByRole('heading', { name: 'Не удалось загрузить состояние проекта' }),
  ).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Попробовать снова' })).toBeTruthy();
});

test('executor can edit terminal stage content without a status control', async () => {
  const terminalStage = {
    ...stage('terminal-stage', 'Completed stage'),
    status: 'completed',
  };
  const fetchMock = stateFetch(executorId, { stages: [terminalStage] });
  renderPage(fetchMock, executor);

  expect(await screen.findByRole('heading', { name: 'Completed stage' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Изменить этап' }));

  const stageCard = screen.getByRole('heading', { name: 'Completed stage' }).closest('article');
  if (!stageCard) throw new Error('The completed stage card was not rendered.');
  expect(screen.getByText('Статус: Завершён')).toBeTruthy();
  expect(screen.queryByRole('combobox', { name: 'Status' })).toBeNull();
  fireEvent.change(within(stageCard).getByLabelText('Название этапа'), {
    target: { value: 'Updated completed stage' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить этап' }));

  await waitFor(() => {
    const patchCall = fetchMock.mock.calls.find(
      ([url, init]) => String(url) === '/api/v1/stages/terminal-stage/' && init?.method === 'PATCH',
    );
    expect(patchCall).toBeTruthy();
    expect(JSON.parse(String(patchCall?.[1]?.body))).not.toHaveProperty('status');
  });
  expect(await screen.findByRole('heading', { name: 'Updated completed stage' })).toBeTruthy();
});

test.each(['resolved', 'dismissed'] as const)(
  'executor cannot edit a %s conflict',
  async (status) => {
    const conflict: StateTestConflict = {
      id: 'terminal-conflict',
      title: `${status === 'resolved' ? 'Resolved' : 'Dismissed'} conflict`,
      description: '',
      status,
      resolution: 'Use the approved scope.',
      evidence: [],
      resolved_by_id: executorId,
      resolved_at: '2026-11-12T00:00:00Z',
      created_by_id: executorId,
      created_at: '2026-11-12T00:00:00Z',
      updated_at: '2026-11-12T00:00:00Z',
    };
    const fetchMock = stateFetch(executorId, { stages: [], conflicts: [conflict] });
    renderPage(fetchMock, executor);

    expect(
      await screen.findByRole('heading', {
        name: `${status === 'resolved' ? 'Resolved' : 'Dismissed'} conflict`,
      }),
    ).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Изменить противоречие' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Разрешить противоречие' })).toBeNull();
    expect(screen.queryByRole('combobox', { name: 'Status' })).toBeNull();
    expect(screen.queryByLabelText('Решение')).toBeNull();
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url) === '/api/v1/conflicts/terminal-conflict/' && init?.method === 'PATCH',
      ),
    ).toBe(false);
  },
);
