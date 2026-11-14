import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router';
import type { QuestionnaireSubmission } from '../../../entities/questionnaire';
import { afterEach, expect, test, vi } from 'vitest';
import type { User } from '../../../entities/user';
import { QuestionnairePage } from './QuestionnairePage';

const projectId = '6ca97aa8-c301-43e4-88e0-e83eab67ae8b';
const customerId = '4f20aed8-e14f-47a2-aea8-e225bfe99b5f';
const customer: User = {
  id: customerId,
  email: 'customer@example.com',
  first_name: 'Casey',
  last_name: 'Customer',
  email_verified: true,
  email_verified_at: '2026-11-12T00:00:00Z',
};
const executor: User = {
  id: '3b01fd64-61c8-4d99-a92c-ab13f5141ee1',
  email: 'executor@example.com',
  first_name: 'Erin',
  last_name: 'Executor',
  email_verified: true,
  email_verified_at: '2026-11-12T00:00:00Z',
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function questionnaireSchema() {
  return {
    schema_key: 'website',
    project_type: 'website',
    version: 1,
    questions: [
      { key: 'goal', label: 'What is the main goal?', type: 'textarea', required: true },
      {
        key: 'has_integrations',
        label: 'Does it need integrations?',
        type: 'boolean',
        required: true,
      },
      {
        key: 'integrations',
        label: 'Which services?',
        type: 'string_list',
        required: true,
        min_items: 1,
        visible_if: { question: 'has_integrations', equals: true },
      },
      {
        key: 'has_existing_site',
        label: 'Does a site already exist?',
        type: 'boolean',
        required: true,
      },
      {
        key: 'existing_site_url',
        label: 'Existing website address',
        type: 'url',
        required: true,
        visible_if: { question: 'has_existing_site', equals: true },
      },
    ],
  };
}

function answer(
  question_key: string,
  value: unknown,
  origin: 'prefilled' | 'customer' = 'customer',
) {
  return {
    question_key,
    value,
    origin,
    is_confirmed: false,
    updated_at: '2026-11-12T00:00:00Z',
  };
}

function submission(answers: ReturnType<typeof answer>[]): QuestionnaireSubmission {
  return {
    id: '5c4d755c-0f1f-4caf-99af-fcf7cf5c5ac6',
    project_id: projectId,
    schema_key: 'website',
    schema_version: 1,
    passport_version: 1,
    status: 'draft',
    started_by_id: customerId,
    started_at: '2026-11-12T00:00:00Z',
    submitted_by_id: null,
    submitted_at: null,
    supersedes_id: null,
    answers,
  };
}

function renderPage(fetchMock: ReturnType<typeof vi.fn>, pageUser: User = customer) {
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=questionnaire-test-token',
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/projects/${projectId}/questionnaire`]}>
        <Routes>
          <Route element={<Outlet context={pageUser} />}>
            <Route path="/app/projects/:projectId/questionnaire" element={<QuestionnairePage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test('customer starts, branches, saves, and resumes the schema-authored questionnaire draft', async () => {
  let draft: ReturnType<typeof submission> | null = null;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === `/api/v1/projects/${projectId}/`) {
      return jsonResponse({ id: projectId, status: 'active', project_type: 'website' });
    }
    if (path === `/api/v1/projects/${projectId}/members/`) {
      return jsonResponse([{ user_id: customerId, role: 'customer' }]);
    }
    if (path === `/api/v1/projects/${projectId}/questionnaire/`) {
      return jsonResponse({
        schema: questionnaireSchema(),
        submission: draft,
        history: draft ? [draft] : [],
      });
    }
    if (path === `/api/v1/projects/${projectId}/questionnaire/submissions/`) {
      expect(init?.method).toBe('POST');
      draft = submission([
        answer('goal', 'Passport goal', 'prefilled'),
        answer('has_integrations', false, 'prefilled'),
        answer('has_existing_site', false, 'customer'),
      ]);
      return jsonResponse(draft, 201);
    }
    if (path === `/api/v1/questionnaire/submissions/${draft?.id}/answers/`) {
      expect(init?.method).toBe('PATCH');
      const body = JSON.parse(String(init?.body)) as { answers: Record<string, unknown> };
      expect(body.answers).toEqual({
        has_existing_site: true,
        goal: 'Customer goal',
        existing_site_url: 'https://example.com',
      });
      expect(body.answers.has_existing_site).toBe(true);
      expect(body.answers.existing_site_url).toBe('https://example.com');
      draft = submission([
        answer('goal', String(body.answers.goal), 'customer'),
        answer('has_integrations', false, 'customer'),
        answer('has_existing_site', true, 'customer'),
        answer('existing_site_url', 'https://example.com', 'customer'),
      ]);
      return jsonResponse(draft);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  renderPage(fetchMock);

  expect(await screen.findByRole('heading', { name: 'Анкета заказчика' })).toBeTruthy();
  expect(await screen.findByText('Сайт · версия 1')).toBeTruthy();
  expect(screen.getByText('Черновик ещё не создан.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Заполнить анкету' }));

  expect(await screen.findByLabelText(/Какова главная цель/)).toHaveProperty(
    'value',
    'Passport goal',
  );
  expect(screen.getAllByText('Из паспорта')).toHaveLength(2);
  expect(screen.queryByLabelText('Which services?')).toBeNull();
  expect(screen.queryByLabelText(/Какой адрес существующего сайта/)).toBeNull();

  fireEvent.change(screen.getByLabelText(/Нужно обновить или заменить существующий сайт/), {
    target: { value: 'true' },
  });
  expect(await screen.findByLabelText(/Какой адрес существующего сайта/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText(/Какова главная цель/), {
    target: { value: 'Customer goal' },
  });
  fireEvent.change(screen.getByLabelText(/Какой адрес существующего сайта/), {
    target: { value: 'https://example.com' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить черновик' }));

  expect(await screen.findByText('Черновик сохранён.')).toBeTruthy();
  expect(screen.getByLabelText(/Какова главная цель/)).toHaveProperty('value', 'Customer goal');
});

test('customer keeps local answers after a recoverable draft save error and can retry', async () => {
  let draft: ReturnType<typeof submission> | null = submission([
    answer('goal', 'Passport goal', 'prefilled'),
    answer('has_integrations', false, 'prefilled'),
    answer('has_existing_site', false, 'customer'),
  ]);
  let saves = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === `/api/v1/projects/${projectId}/`) {
      return jsonResponse({ id: projectId, status: 'active', project_type: 'website' });
    }
    if (path === `/api/v1/projects/${projectId}/members/`) {
      return jsonResponse([{ user_id: customerId, role: 'customer' }]);
    }
    if (path === `/api/v1/projects/${projectId}/questionnaire/`) {
      return jsonResponse({
        schema: questionnaireSchema(),
        submission: draft,
        history: draft ? [draft] : [],
      });
    }
    if (path === `/api/v1/questionnaire/submissions/${draft?.id}/answers/`) {
      saves += 1;
      if (saves === 1) return jsonResponse({ code: 'unavailable', detail: 'Try again.' }, 503);
      draft = submission([answer('goal', 'Unsaved goal'), answer('has_existing_site', false)]);
      return jsonResponse(draft);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  renderPage(fetchMock);

  const goal = await screen.findByLabelText(/Какова главная цель/);
  fireEvent.change(goal, { target: { value: 'Unsaved goal' } });
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить черновик' }));
  expect(await screen.findByText('Не удалось выполнить запрос. Попробуйте ещё раз.')).toBeTruthy();
  expect(screen.getByLabelText(/Какова главная цель/)).toHaveProperty('value', 'Unsaved goal');

  fireEvent.click(screen.getByRole('button', { name: 'Повторить сохранение' }));
  expect(await screen.findByText('Черновик сохранён.')).toBeTruthy();
  expect(saves).toBe(2);
});

test('select and boolean questions describe their validation errors', async () => {
  const draft = submission([]);
  const schema = questionnaireSchema();
  schema.questions.push({ key: 'trigger_type', label: 'Trigger', type: 'select', required: true });
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === `/api/v1/projects/${projectId}/`)
      return jsonResponse({ id: projectId, status: 'active', project_type: 'website' });
    if (path === `/api/v1/projects/${projectId}/members/`)
      return jsonResponse([{ user_id: customerId, role: 'customer' }]);
    if (path === `/api/v1/projects/${projectId}/questionnaire/`)
      return jsonResponse({ schema, submission: draft, history: [draft] });
    if (path === `/api/v1/questionnaire/submissions/${draft.id}/answers/`)
      return jsonResponse(
        { detail: 'Invalid', errors: { has_integrations: ['Required'], trigger_type: ['Required'] } },
        400,
      );
    throw new Error(`Unexpected request: ${path}`);
  });
  renderPage(fetchMock);
  await screen.findByLabelText(/Нужны ли интеграции/);
  fireEvent.change(screen.getByLabelText(/Какова главная цель/), { target: { value: 'Goal' } });
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить черновик' }));
  await waitFor(() => {
    for (const name of [/Нужны ли интеграции/, /Trigger/]) {
      const field = screen.getByLabelText(name);
      const errorId = field.getAttribute('aria-describedby');
      expect(errorId).toBeTruthy();
      if (!errorId) throw new Error('The field has no error description.');
      expect(document.getElementById(errorId)).toBeTruthy();
    }
  });
});

test('customer confirms prefilled answers and sees the submitted version locked', async () => {
  let current = submission([
    answer('goal', 'Passport goal', 'prefilled'),
    answer('has_integrations', false, 'prefilled'),
    answer('has_existing_site', false, 'customer'),
  ]);
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === `/api/v1/projects/${projectId}/`) {
      return jsonResponse({ id: projectId, status: 'active', project_type: 'website' });
    }
    if (path === `/api/v1/projects/${projectId}/members/`) {
      return jsonResponse([{ user_id: customerId, role: 'customer' }]);
    }
    if (path === `/api/v1/projects/${projectId}/questionnaire/`) {
      return jsonResponse({
        schema: questionnaireSchema(),
        submission: current,
        history: [current],
      });
    }
    if (path === `/api/v1/questionnaire/submissions/${current.id}/submit/`) {
      expect(init?.method).toBe('POST');
      expect(JSON.parse(String(init?.body))).toEqual({ confirm_prefilled: true });
      current = {
        ...current,
        status: 'submitted',
        submitted_by_id: customerId,
        submitted_at: '2026-11-12T00:01:00Z',
        answers: current.answers.map((savedAnswer) => ({ ...savedAnswer, is_confirmed: true })),
      };
      return jsonResponse(current);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  renderPage(fetchMock);

  expect(await screen.findByRole('heading', { name: 'Анкета заказчика' })).toBeTruthy();
  const confirm = await screen.findByRole('checkbox', {
    name: /подтверждаю ответы, заполненные из паспорта/i,
  });
  const submit = screen.getByRole('button', { name: 'Отправить ответы' }) as HTMLButtonElement;
  expect(submit.disabled).toBe(true);
  fireEvent.click(confirm);
  fireEvent.click(submit);

  expect(await screen.findByText('Ответы отправлены и заблокированы для изменений.')).toBeTruthy();
  expect(screen.queryByLabelText(/Какова главная цель/)).toBeNull();
  expect(screen.getByText('Passport goal')).toBeTruthy();
});

test('customer refreshes a stale draft version without losing answers before retrying submit', async () => {
  let current = submission([
    answer('goal', 'Initial goal'),
    answer('has_integrations', false),
    answer('has_existing_site', false),
  ]);
  let submitCalls = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === `/api/v1/projects/${projectId}/`) {
      return jsonResponse({ id: projectId, status: 'active', project_type: 'website' });
    }
    if (path === `/api/v1/projects/${projectId}/members/`) {
      return jsonResponse([{ user_id: customerId, role: 'customer' }]);
    }
    if (path === `/api/v1/projects/${projectId}/questionnaire/`) {
      return jsonResponse({
        schema: questionnaireSchema(),
        submission: current,
        history: [current],
      });
    }
    if (path === `/api/v1/questionnaire/submissions/${current.id}/answers/`) {
      expect(init?.method).toBe('PATCH');
      current = {
        ...current,
        answers: current.answers.map((savedAnswer) =>
          savedAnswer.question_key === 'goal'
            ? { ...savedAnswer, value: 'Reviewed goal', origin: 'customer' }
            : savedAnswer,
        ),
      };
      return jsonResponse(current);
    }
    if (path === `/api/v1/questionnaire/submissions/${current.id}/submit/`) {
      submitCalls += 1;
      if (submitCalls === 1) {
        return jsonResponse(
          {
            code: 'conflict',
            detail: 'The project passport changed after this draft started.',
          },
          409,
        );
      }
      current = {
        ...current,
        status: 'submitted',
        submitted_by_id: customerId,
        submitted_at: '2026-11-12T00:01:00Z',
      };
      return jsonResponse(current);
    }
    if (path === `/api/v1/questionnaire/submissions/${current.id}/refresh-passport-version/`) {
      expect(init?.method).toBe('POST');
      current = { ...current, passport_version: 2 };
      return jsonResponse(current);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  renderPage(fetchMock);

  const goal = await screen.findByLabelText(/Какова главная цель/);
  fireEvent.change(goal, { target: { value: 'Reviewed goal' } });
  fireEvent.click(screen.getByRole('button', { name: 'Отправить ответы' }));
  expect(
    await screen.findByText(/Паспорт проекта изменился после создания черновика/),
  ).toBeTruthy();
  expect(screen.getByLabelText(/Какова главная цель/)).toHaveProperty('value', 'Reviewed goal');

  fireEvent.click(screen.getByRole('button', { name: 'Обновить версию черновика' }));
  expect(
    await screen.findByText('Версия черновика обновлена. Проверьте ответы и отправьте их снова.'),
  ).toBeTruthy();
  expect(screen.getByLabelText(/Какова главная цель/)).toHaveProperty('value', 'Reviewed goal');
  fireEvent.click(screen.getByRole('button', { name: 'Отправить ответы' }));

  expect(await screen.findByText('Ответы отправлены и заблокированы для изменений.')).toBeTruthy();
  expect(submitCalls).toBe(2);
});

test('executor sees conflicts, keeps the passport value, and can request a correction', async () => {
  const submitted = {
    ...submission([answer('goal', 'Customer goal')]),
    status: 'submitted',
    passport_version: 2,
    submitted_by_id: customerId,
    submitted_at: '2026-11-12T00:01:00Z',
  };
  let current = submitted;
  let conflicts = [
    {
      id: '2f497888-72dd-48bb-8454-8bf763a22e01',
      submission_id: submitted.id,
      question_key: 'goal',
      mapped_field: 'goal',
      passport_value: 'Executor goal' as unknown,
      answer_value: 'Customer goal' as unknown,
      status: 'pending',
      decision: null,
      reviewed_by_id: null,
      created_at: '2026-11-12T00:01:00Z',
      resolved_at: null,
    },
  ];
  conflicts.push({
    ...conflicts[0],
    id: 'boolean-conflict',
    question_key: 'has_existing_site',
    passport_value: true,
    answer_value: false,
  });
  const conflictId = conflicts[0].id;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === `/api/v1/projects/${projectId}/`) {
      return jsonResponse({ id: projectId, status: 'active', project_type: 'website' });
    }
    if (path === `/api/v1/projects/${projectId}/members/`) {
      return jsonResponse([{ user_id: executor.id, role: 'executor' }]);
    }
    if (path === `/api/v1/projects/${projectId}/questionnaire/`) {
      return jsonResponse({
        schema: questionnaireSchema(),
        submission: current,
        history: [current],
      });
    }
    if (path === `/api/v1/projects/${projectId}/questionnaire/conflicts/`) {
      return jsonResponse(conflicts);
    }
    if (path === `/api/v1/projects/${projectId}/passport/`) {
      return jsonResponse({ version: 2 });
    }
    if (path === `/api/v1/questionnaire/conflicts/${conflictId}/resolve/`) {
      expect(init?.method).toBe('POST');
      expect(JSON.parse(String(init?.body))).toEqual({
        decision: 'keep_passport',
        expected_passport_version: 2,
      });
      const conflict = conflicts[0];
      conflicts = [];
      return jsonResponse({ ...conflict, status: 'resolved', decision: 'keep_passport' });
    }
    if (path === `/api/v1/questionnaire/submissions/${submitted.id}/request-correction/`) {
      expect(init?.method).toBe('POST');
      current = {
        ...submitted,
        id: '9b7f75c4-638c-4f5b-a863-d6a363ac7f27',
        status: 'draft',
        supersedes_id: submitted.id,
      };
      return jsonResponse(current);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  renderPage(fetchMock, executor);

  expect(await screen.findByText('Да')).toBeTruthy();
  expect(screen.getAllByRole('heading', { name: 'Цель проекта' })).toHaveLength(2);
  expect(screen.getByText('Нет')).toBeTruthy();
  expect(await screen.findByText('Executor goal')).toBeTruthy();
  expect(screen.getAllByText('Customer goal')).toHaveLength(2);
  const keepButton = screen.getAllByRole('button', { name: 'Оставить значение паспорта' })[0];
  await waitFor(() => expect(keepButton).toHaveProperty('disabled', false));
  fireEvent.click(keepButton);
  await waitFor(() => expect(screen.queryByText('Executor goal')).toBeNull());
  expect(screen.getByText('Да')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Запросить исправления' }));
  expect(await screen.findAllByText('Черновик исправлений')).toHaveLength(2);
});
