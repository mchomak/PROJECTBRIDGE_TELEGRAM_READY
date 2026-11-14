import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router';
import type { User } from '../../../entities/user';
import { ProjectSpecificationPage } from './ProjectSpecificationPage';

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

function generationRecord(status: string, errorCode = '') {
  return {
    id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    status,
    expected_version: 1,
    error_code: errorCode,
    created_at: '2026-11-12T12:00:00Z',
    started_at: null,
    completed_at: null,
  };
}

function specificationRecord(content = '', version = 1, generation: unknown = null) {
  return {
    id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    project_id: projectId,
    content,
    status: content ? 'ready' : 'draft',
    updated_by_id: executorId,
    version,
    created_at: '2026-11-12T10:00:00Z',
    updated_at: '2026-11-12T10:00:00Z',
    generation,
  };
}

function renderPage(fetchMock: ReturnType<typeof vi.fn>, pageUser: User) {
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=specification-page-test-token',
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/projects/${projectId}/specification`]}>
        <Routes>
          <Route element={<Outlet context={pageUser} />}>
            <Route
              path="/app/projects/:projectId/specification"
              element={<ProjectSpecificationPage />}
            />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function specificationFetch({
  projectStatus = 'active',
  staleSave = false,
  closeProjectOnStaleSave = false,
  generationConflictCloseProject = false,
  generationStatus,
  generationError = '',
  completeAfterPoll = false,
  recoverDispatchWarning = false,
}: {
  projectStatus?: string;
  staleSave?: boolean;
  closeProjectOnStaleSave?: boolean;
  generationConflictCloseProject?: boolean;
  generationStatus?: string;
  generationError?: string;
  completeAfterPoll?: boolean;
  recoverDispatchWarning?: boolean;
} = {}) {
  let currentProjectStatus = projectStatus;
  let specificationPolls = 0;
  let specification = specificationRecord(
    '# Current draft',
    1,
    generationStatus ? generationRecord(generationStatus, generationError) : null,
  );
  let generationStarted = false;
  let generationPolls = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (url === `/api/v1/projects/${projectId}/`) {
      return jsonResponse({
        id: projectId,
        name: 'Telegram delivery bot',
        description: 'A shared project',
        project_type: 'telegram_bot',
        status: currentProjectStatus,
        created_by_id: executorId,
        created_at: '2026-11-12T00:00:00Z',
        updated_at: '2026-11-12T00:00:00Z',
      });
    }
    if (url === `/api/v1/projects/${projectId}/members/`) {
      return jsonResponse([
        { id: executorId, user_id: executorId, role: 'executor' },
        { id: customerId, user_id: customerId, role: 'customer' },
      ]);
    }
    if (url === `/api/v1/projects/${projectId}/specification/` && method === 'GET') {
      specificationPolls += 1;
      const currentGeneration = specification.generation;
      if (
        recoverDispatchWarning &&
        specificationPolls > 1 &&
        currentGeneration !== null &&
        typeof currentGeneration === 'object' &&
        'error_code' in currentGeneration &&
        typeof currentGeneration.error_code === 'string' &&
        ['queue_unavailable', 'worker_backlog'].includes(currentGeneration.error_code)
      ) {
        specification = {
          ...specification,
          generation: generationRecord('queued'),
        };
      }
      if (generationStarted) {
        generationPolls += 1;
        specification =
          completeAfterPoll && generationPolls >= 2
            ? specificationRecord(
                '# Generated draft without reload',
                2,
                generationRecord('succeeded'),
              )
            : {
                ...specification,
                generation: generationRecord('queued'),
              };
      }
      return jsonResponse(specification);
    }
    if (url === `/api/v1/projects/${projectId}/specification/` && method === 'PATCH') {
      if (staleSave) {
        if (closeProjectOnStaleSave) {
          currentProjectStatus = 'completed';
        } else {
          specification = specificationRecord(
            '# Another editor saved first',
            specification.version + 1,
          );
        }
        return jsonResponse(
          {
            code: 'conflict',
            detail: 'The specification changed after it was loaded.',
            errors: null,
            request_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
          },
          409,
        );
      }
      const body = JSON.parse(String(init?.body));
      specification = specificationRecord(body.content, specification.version + 1);
      return jsonResponse(specification);
    }
    if (url === `/api/v1/projects/${projectId}/specification/generate/` && method === 'POST') {
      if (generationConflictCloseProject) {
        currentProjectStatus = 'completed';
        return jsonResponse(
          {
            code: 'conflict',
            detail: 'The project is no longer writable.',
            errors: null,
            request_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
          },
          409,
        );
      }
      generationStarted = true;
      return jsonResponse(generationRecord('queued'), 202);
    }
    throw new Error(`Unhandled request: ${method} ${url}`);
  });
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test('executor can edit and save the current Markdown version', async () => {
  const fetchMock = specificationFetch();
  renderPage(fetchMock, executor);

  const editor = await screen.findByRole('textbox', { name: 'Текст Markdown' });
  fireEvent.input(editor, { target: { value: '# Revised draft' } });
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить спецификацию' }));

  expect(await screen.findByText('Saved version 2.')).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith(
    `/api/v1/projects/${projectId}/specification/`,
    expect.objectContaining({
      method: 'PATCH',
      body: JSON.stringify({ content: '# Revised draft', version: 1 }),
    }),
  );
});

test('executor can clear the Markdown draft and save an empty body', async () => {
  const fetchMock = specificationFetch();
  renderPage(fetchMock, executor);

  const editor = await screen.findByRole('textbox', { name: 'Текст Markdown' });
  fireEvent.input(editor, { target: { value: '' } });
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить спецификацию' }));

  expect(await screen.findByText('Saved version 2.')).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith(
    `/api/v1/projects/${projectId}/specification/`,
    expect.objectContaining({
      method: 'PATCH',
      body: JSON.stringify({ content: '', version: 1 }),
    }),
  );
});

test('executor can queue async generation and sees the polling state', async () => {
  const fetchMock = specificationFetch();
  renderPage(fetchMock, executor);

  fireEvent.click(await screen.findByRole('button', { name: 'Создать черновик' }));

  expect(await screen.findByText('Ожидание начала создания')).toBeTruthy();
  const generateCall = fetchMock.mock.calls.find(
    ([url, init]) =>
      String(url) === `/api/v1/projects/${projectId}/specification/generate/` &&
      init?.method === 'POST',
  );
  expect(new Headers(generateCall?.[1]?.headers).get('Idempotency-Key')).toMatch(
    /^[0-9a-f-]{36}$/i,
  );
});

test.each(['queue_unavailable', 'worker_backlog'])(
  'queued generation explains that no worker has started for %s and clears the warning after recovery',
  async (warningCode) => {
    const fetchMock = specificationFetch({
      generationStatus: 'queued',
      generationError: warningCode,
      recoverDispatchWarning: true,
    });
    renderPage(fetchMock, executor);

    expect(await screen.findByText('Создание ещё не запущено')).toBeTruthy();
    const warning =
      'Создание ожидает обработки. Система продолжит попытки; текущий черновик не изменён.';
    expect(await screen.findByText(warning)).toBeTruthy();
    await waitFor(
      () => {
        expect(screen.queryByText(warning)).toBeNull();
        expect(screen.getByText('Ожидание начала создания')).toBeTruthy();
      },
      { timeout: 5_000 },
    );
  },
);

test('executor sees generated content after polling completes without reloading', async () => {
  const fetchMock = specificationFetch({ completeAfterPoll: true });
  renderPage(fetchMock, executor);

  fireEvent.click(await screen.findByRole('button', { name: 'Создать черновик' }));

  expect(await screen.findByText('Ожидание начала создания')).toBeTruthy();
  await waitFor(
    () => {
      expect(screen.getByText('Последнее создание завершено')).toBeTruthy();
      expect(
        (screen.getByRole('textbox', { name: 'Текст Markdown' }) as HTMLTextAreaElement).value,
      ).toBe('# Generated draft without reload');
    },
    { timeout: 5_000 },
  );
  expect(
    fetchMock.mock.calls.filter(
      ([url, init]) =>
        String(url) === `/api/v1/projects/${projectId}/specification/` && init?.method !== 'PATCH',
    ).length,
  ).toBeGreaterThan(2);
});

test('customer sees the shared draft without editing or generation controls', async () => {
  const fetchMock = specificationFetch();
  renderPage(fetchMock, customer);

  expect(await screen.findByText('# Current draft')).toBeTruthy();
  expect(screen.queryByRole('textbox', { name: 'Текст Markdown' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Создать черновик' })).toBeNull();
});

test('executor sees stale-save conflict while their unsaved text remains', async () => {
  const fetchMock = specificationFetch({ staleSave: true });
  renderPage(fetchMock, executor);

  const editor = await screen.findByRole('textbox', { name: 'Текст Markdown' });
  fireEvent.input(editor, { target: { value: '# My unsaved edit' } });
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить спецификацию' }));

  expect(
    await screen.findByRole('heading', {
      name: 'Спецификация изменилась на сервере',
    }),
  ).toBeTruthy();
  expect((editor as HTMLTextAreaElement).value).toBe('# My unsaved edit');
  expect(screen.getByRole('button', { name: 'Загрузить последнюю версию' })).toBeTruthy();
});

test('executor becomes read-only and keeps unsaved text if the project closes elsewhere', async () => {
  const fetchMock = specificationFetch({
    staleSave: true,
    closeProjectOnStaleSave: true,
  });
  renderPage(fetchMock, executor);

  const editor = await screen.findByRole('textbox', { name: 'Текст Markdown' });
  fireEvent.input(editor, { target: { value: '# My unsaved edit' } });
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить спецификацию' }));

  expect(
    await screen.findByText(
      'Проект закрыт до сохранения изменений. Спецификация доступна только для чтения; несохранённый текст приведён ниже.',
    ),
  ).toBeTruthy();
  expect(screen.queryByRole('textbox', { name: 'Текст Markdown' })).toBeNull();
  expect(screen.getByRole('heading', { name: 'Ваши несохранённые изменения' })).toBeTruthy();
  expect(screen.getByText('# My unsaved edit')).toBeTruthy();
});

test('generation conflict refetches a project closed in another tab', async () => {
  const fetchMock = specificationFetch({ generationConflictCloseProject: true });
  renderPage(fetchMock, executor);

  fireEvent.click(await screen.findByRole('button', { name: 'Создать черновик' }));

  expect(
    await screen.findByText(
      'Проект закрыт во время запуска создания. Спецификация доступна только для чтения.',
    ),
  ).toBeTruthy();
  expect(screen.getByText('Для закрытых проектов доступен только просмотр')).toBeTruthy();
  expect(screen.queryByRole('textbox', { name: 'Текст Markdown' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Создать черновик' })).toBeNull();
  expect(
    fetchMock.mock.calls.filter(([url]) => String(url) === `/api/v1/projects/${projectId}/`).length,
  ).toBeGreaterThan(1);
});

test('completed projects show a read-only specification to the executor', async () => {
  const fetchMock = specificationFetch({ projectStatus: 'completed' });
  renderPage(fetchMock, executor);

  expect(await screen.findByText('# Current draft')).toBeTruthy();
  expect(screen.getByText('Для закрытых проектов доступен только просмотр')).toBeTruthy();
  expect(screen.queryByRole('textbox', { name: 'Текст Markdown' })).toBeNull();
});

test('executor receives an actionable message when generation context is too large', async () => {
  const fetchMock = specificationFetch({
    generationStatus: 'failed',
    generationError: 'source_context_too_large',
  });
  renderPage(fetchMock, executor);

  expect(
    await screen.findByText(
      'The approved passport and shared Project State exceed the 24,000-byte generation limit. Shorten long text or remove unnecessary detail, then try again.',
    ),
  ).toBeTruthy();
});

test('executor can retry after bounded worker-dispatch recovery is exhausted', async () => {
  const fetchMock = specificationFetch({
    generationStatus: 'failed',
    generationError: 'queue_unavailable',
  });
  renderPage(fetchMock, executor);

  expect(
    await screen.findByText(
      'Не удалось связаться с обработчиком после нескольких попыток. Текущий черновик сохранён; можно запустить создание заново.',
    ),
  ).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Создать черновик' })).toBeTruthy();
});
