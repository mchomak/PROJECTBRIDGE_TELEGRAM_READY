import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
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

  expect(await screen.findByRole('heading', { name: 'Customer questionnaire' })).toBeTruthy();
  expect(await screen.findByText('Website · version 1')).toBeTruthy();
  expect(screen.getByText('No draft has been started yet.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Start questionnaire' }));

  expect(await screen.findByLabelText(/What is the main goal/)).toHaveProperty(
    'value',
    'Passport goal',
  );
  expect(screen.getAllByText('From passport')).toHaveLength(2);
  expect(screen.queryByLabelText('Which services?')).toBeNull();
  expect(screen.queryByLabelText(/Existing website address/)).toBeNull();

  fireEvent.change(screen.getByLabelText(/Does a site already exist/), {
    target: { value: 'true' },
  });
  expect(await screen.findByLabelText(/Existing website address/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText(/What is the main goal/), {
    target: { value: 'Customer goal' },
  });
  fireEvent.change(screen.getByLabelText(/Existing website address/), {
    target: { value: 'https://example.com' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));

  expect(await screen.findByText('Draft saved.')).toBeTruthy();
  expect(screen.getByLabelText(/What is the main goal/)).toHaveProperty('value', 'Customer goal');
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

  const goal = await screen.findByLabelText(/What is the main goal/);
  fireEvent.change(goal, { target: { value: 'Unsaved goal' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
  expect(await screen.findByText('Try again.')).toBeTruthy();
  expect(screen.getByLabelText(/What is the main goal/)).toHaveProperty('value', 'Unsaved goal');

  fireEvent.click(screen.getByRole('button', { name: 'Try save again' }));
  expect(await screen.findByText('Draft saved.')).toBeTruthy();
  expect(saves).toBe(2);
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

  expect(await screen.findByRole('heading', { name: 'Customer questionnaire' })).toBeTruthy();
  const confirm = await screen.findByRole('checkbox', {
    name: /confirm the answers prefilled from the passport/i,
  });
  const submit = screen.getByRole('button', { name: 'Submit answers' }) as HTMLButtonElement;
  expect(submit.disabled).toBe(true);
  fireEvent.click(confirm);
  fireEvent.click(submit);

  expect(await screen.findByText('Submitted. Answers are locked.')).toBeTruthy();
  expect(screen.queryByLabelText(/What is the main goal/)).toBeNull();
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

  const goal = await screen.findByLabelText(/What is the main goal/);
  fireEvent.change(goal, { target: { value: 'Reviewed goal' } });
  fireEvent.click(screen.getByRole('button', { name: 'Submit answers' }));
  expect(await screen.findByText(/Your draft is safe/)).toBeTruthy();
  expect(screen.getByLabelText(/What is the main goal/)).toHaveProperty('value', 'Reviewed goal');

  fireEvent.click(screen.getByRole('button', { name: 'Refresh draft version' }));
  expect(
    await screen.findByText('Draft version refreshed. Review your answers and submit again.'),
  ).toBeTruthy();
  expect(screen.getByLabelText(/What is the main goal/)).toHaveProperty('value', 'Reviewed goal');
  fireEvent.click(screen.getByRole('button', { name: 'Submit answers' }));

  expect(await screen.findByText('Submitted. Answers are locked.')).toBeTruthy();
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
      passport_value: 'Executor goal',
      answer_value: 'Customer goal',
      status: 'pending',
      decision: null,
      reviewed_by_id: null,
      created_at: '2026-11-12T00:01:00Z',
      resolved_at: null,
    },
  ];
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

  expect(await screen.findByText('Executor goal')).toBeTruthy();
  expect(screen.getAllByText('Customer goal')).toHaveLength(2);
  fireEvent.click(screen.getByRole('button', { name: 'Keep passport value' }));
  expect(await screen.findByText('No unresolved questionnaire conflicts.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Request correction' }));
  expect(await screen.findAllByText('Correction draft')).toHaveLength(2);
});
