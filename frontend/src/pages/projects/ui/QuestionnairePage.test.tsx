import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router';
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

function submission(answers: ReturnType<typeof answer>[]) {
  return {
    id: '5c4d755c-0f1f-4caf-99af-fcf7cf5c5ac6',
    project_id: projectId,
    schema_key: 'website',
    schema_version: 1,
    status: 'draft',
    started_at: '2026-11-12T00:00:00Z',
    answers,
  };
}

function renderPage(fetchMock: ReturnType<typeof vi.fn>) {
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
          <Route element={<Outlet context={customer} />}>
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
      return jsonResponse({ schema: questionnaireSchema(), submission: draft });
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
      return jsonResponse({ schema: questionnaireSchema(), submission: draft });
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
