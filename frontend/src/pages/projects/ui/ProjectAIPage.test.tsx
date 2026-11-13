import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router';
import type { User } from '../../../entities/user';
import { ProjectAIPage } from './ProjectAIPage';

const projectId = '1e3ae97f-6517-4eac-b81f-b94d34c73f2e';
const executorId = 'b2e3d4f1-65d0-463c-ac4f-68674cf57822';
const customerId = '497a8eb7-fb6a-405b-a8ce-6d8c2d87231d';
const proposalIds = [
  '33333333-3333-4333-8333-333333333331',
  '33333333-3333-4333-8333-333333333332',
  '33333333-3333-4333-8333-333333333333',
  '33333333-3333-4333-8333-333333333334',
];

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

function requestRecord(
  status = 'succeeded',
  resultCount = 3,
  id = '22222222-2222-4222-8222-222222222222',
  errorCode = '',
) {
  return {
    id,
    status,
    result_count: resultCount,
    error_code: errorCode,
    created_at: '2026-11-12T12:00:00Z',
    started_at: '2026-11-12T12:00:01Z',
    completed_at: '2026-11-12T12:00:04Z',
    run: null,
  };
}

function proposalRecord(index: number) {
  const title = [
    'Add audit history',
    'Confirm retention period',
    'Support exports',
    'Create export audit bundle',
  ][index];
  return {
    id: proposalIds[index],
    analysis_run_id: '11111111-1111-4111-8111-111111111111',
    proposal_type: index === 1 ? 'open_question_create' : 'requirement_create',
    title,
    description: `Suggested change ${index + 1}.`,
    rationale: 'The project evidence supports executor review.',
    proposed_payload:
      index === 1
        ? { question: 'Which retention period is required?' }
        : { title, description: 'Keep an audit trail.' },
    final_payload: null,
    status: 'pending',
    reviewed_by_id: null,
    reviewed_at: null,
    applied_at: null,
    created_at: '2026-11-12T12:00:00Z',
    evidence: [
      {
        id: `44444444-4444-4444-8444-44444444444${index}`,
        source_type: 'passport',
        source_id: '55555555-5555-4555-8555-555555555555',
        excerpt: 'The workspace must retain a record of important changes.',
        metadata: { version: 2 },
      },
    ],
  };
}

function renderPage(fetchMock: ReturnType<typeof vi.fn>, pageUser: User) {
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=ai-page-test-token',
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/projects/${projectId}/ai`]}>
        <Routes>
          <Route element={<Outlet context={pageUser} />}>
            <Route path="/app/projects/:projectId/ai" element={<ProjectAIPage />} />
            <Route path="/app/projects/:projectId" element={<p>Project overview</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function workspaceFetch({
  completeWithNewProposal = false,
  completeOnFirstPoll = false,
  queueWarningThenRecover = false,
  queueWarningCode = 'worker_backlog',
} = {}) {
  const proposalStatuses = new Map<string, string>();
  let currentRequest = requestRecord();
  let analysisStarted = false;
  let analysisPollCount = 0;
  let newProposalAvailable = false;
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
        { id: 'member-executor', user_id: executorId, role: 'executor' },
        { id: 'member-customer', user_id: customerId, role: 'customer' },
      ]);
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/ai/analyses/`) && method === 'GET') {
      if (queueWarningThenRecover && analysisStarted && currentRequest.status !== 'running') {
        analysisPollCount += 1;
        currentRequest =
          analysisPollCount === 1
            ? requestRecord('queued', 0, '22222222-2222-4222-8222-222222222223', queueWarningCode)
            : requestRecord('running', 0, '22222222-2222-4222-8222-222222222223');
      } else if (
        completeWithNewProposal &&
        analysisStarted &&
        currentRequest.status !== 'succeeded'
      ) {
        analysisPollCount += 1;
        if (completeOnFirstPoll && analysisPollCount === 1) {
          currentRequest = requestRecord('succeeded', 4, '22222222-2222-4222-8222-222222222223');
          newProposalAvailable = true;
        } else {
          if (analysisPollCount === 2) {
            currentRequest = requestRecord('running', 0, '22222222-2222-4222-8222-222222222223');
          }
          if (analysisPollCount >= 3) {
            currentRequest = requestRecord('succeeded', 4, '22222222-2222-4222-8222-222222222223');
            newProposalAvailable = true;
          }
        }
      }
      return jsonResponse({ count: 1, next: null, previous: null, results: [currentRequest] });
    }
    if (url.startsWith(`/api/v1/projects/${projectId}/ai/proposals/`) && method === 'GET') {
      const visibleProposalIds = newProposalAvailable ? proposalIds : proposalIds.slice(0, 3);
      return jsonResponse({
        count: visibleProposalIds.length,
        next: null,
        previous: null,
        results: visibleProposalIds.map((id, index) => ({
          ...proposalRecord(index),
          status: proposalStatuses.get(id) ?? 'pending',
        })),
      });
    }
    if (url === `/api/v1/projects/${projectId}/ai/analyses/` && method === 'POST') {
      currentRequest = requestRecord('queued', 0, '22222222-2222-4222-8222-222222222223');
      analysisStarted = true;
      return jsonResponse(currentRequest, 202);
    }
    const proposalMatch = url.match(
      /\/api\/v1\/ai\/proposals\/([^/]+)\/(accept|reject|apply-edited)\/$/,
    );
    if (proposalMatch && method === 'POST') {
      const [, proposalId, action] = proposalMatch;
      const nextStatus = action === 'reject' ? 'rejected' : 'applied';
      proposalStatuses.set(proposalId, nextStatus);
      const index = proposalIds.indexOf(proposalId);
      const proposal = {
        ...proposalRecord(index),
        status: nextStatus,
        final_payload: null as unknown,
      };
      if (action === 'apply-edited') {
        const body = JSON.parse(String(init?.body ?? '{}')) as { final_payload?: unknown };
        proposal.final_payload = body.final_payload ?? null;
      }
      return jsonResponse(proposal);
    }
    throw new Error(`Unexpected request: ${method} ${url}`);
  });
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

test('executor sees analysis history and evidence, then can accept, edit, reject, and start analysis', async () => {
  const fetchMock = workspaceFetch();
  renderPage(fetchMock, executor);

  expect(await screen.findByRole('heading', { name: 'AI analysis and proposals' })).toBeTruthy();
  expect(screen.getByRole('heading', { name: 'Analysis history' })).toBeTruthy();
  expect(screen.getByRole('heading', { name: 'Proposal inbox' })).toBeTruthy();
  expect(
    await screen.findAllByText('The workspace must retain a record of important changes.'),
  ).toHaveLength(3);
  expect(screen.getAllByText('55555555-5555-4555-8555-555555555555')).toHaveLength(3);

  const acceptCard = screen.getByRole('article', { name: 'Add audit history' });
  fireEvent.click(within(acceptCard).getByRole('button', { name: 'Accept and apply' }));
  await waitFor(() => expect(within(acceptCard).getByText('applied')).toBeTruthy());

  const editCard = screen.getByRole('article', { name: 'Confirm retention period' });
  fireEvent.click(within(editCard).getByRole('button', { name: 'Edit first' }));
  fireEvent.change(within(editCard).getByLabelText('Edit proposed Project State data'), {
    target: { value: '{"question":"Use a 90 day retention period?"}' },
  });
  fireEvent.click(within(editCard).getByRole('button', { name: 'Apply edited proposal' }));
  await waitFor(() => expect(within(editCard).getByText('applied')).toBeTruthy());
  const editedCall = fetchMock.mock.calls.find(
    ([input, init]) =>
      String(input) === `/api/v1/ai/proposals/${proposalIds[1]}/apply-edited/` &&
      init?.method === 'POST',
  );
  expect(editedCall).toBeTruthy();
  expect(JSON.parse(String(editedCall?.[1]?.body))).toEqual({
    final_payload: { question: 'Use a 90 day retention period?' },
  });

  const rejectCard = screen.getByRole('article', { name: 'Support exports' });
  fireEvent.click(within(rejectCard).getByRole('button', { name: 'Reject' }));
  await waitFor(() => expect(within(rejectCard).getByText('rejected')).toBeTruthy());

  fireEvent.click(screen.getByRole('button', { name: 'Analyze project' }));
  await screen.findByText('Waiting to start');
  const analysisCall = fetchMock.mock.calls.find(
    ([input, init]) =>
      String(input) === `/api/v1/projects/${projectId}/ai/analyses/` && init?.method === 'POST',
  );
  expect(new Headers(analysisCall?.[1]?.headers).get('Idempotency-Key')).toBeTruthy();
});

test('customer is redirected and never loads private analysis or proposal data', async () => {
  const fetchMock = workspaceFetch();
  renderPage(fetchMock, customer);

  expect(await screen.findByText('Project overview')).toBeTruthy();
  expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/ai/'))).toBe(false);
});

test('proposal inbox refreshes when a polled analysis request succeeds', async () => {
  const fetchMock = workspaceFetch({ completeWithNewProposal: true });
  renderPage(fetchMock, executor);

  expect(await screen.findByRole('heading', { name: 'AI analysis and proposals' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Analyze project' }));

  expect(
    await screen.findByRole('article', { name: 'Create export audit bundle' }, { timeout: 9_000 }),
  ).toBeTruthy();
  expect(
    fetchMock.mock.calls.filter(
      ([input, init]) =>
        String(input).startsWith(`/api/v1/projects/${projectId}/ai/proposals/`) &&
        init?.method !== 'POST',
    ).length,
  ).toBeGreaterThan(1);
}, 12_000);

test.each(['queue_unavailable', 'worker_backlog'])(
  'queued analysis explains that work has not started for %s and clears the warning after recovery',
  async (warningCode) => {
    const fetchMock = workspaceFetch({
      queueWarningThenRecover: true,
      queueWarningCode: warningCode,
    });
    renderPage(fetchMock, executor);

    expect(await screen.findByRole('heading', { name: 'AI analysis and proposals' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Analyze project' }));

    const warning =
      'This analysis is waiting for processing. The system will keep retrying; it has not started yet.';
    expect(await screen.findByText(warning, {}, { timeout: 6_000 })).toBeTruthy();
    await waitFor(
      () => {
        expect(screen.queryByText(warning)).toBeNull();
        expect(screen.getByRole('button', { name: 'Analysis in progress' })).toBeTruthy();
      },
      { timeout: 6_000 },
    );
  },
  12_000,
);

test('proposal inbox refreshes when the first poll already reports success', async () => {
  const fetchMock = workspaceFetch({
    completeWithNewProposal: true,
    completeOnFirstPoll: true,
  });
  renderPage(fetchMock, executor);

  expect(await screen.findByRole('heading', { name: 'AI analysis and proposals' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Analyze project' }));

  expect(
    await screen.findByRole('article', { name: 'Create export audit bundle' }, { timeout: 3_000 }),
  ).toBeTruthy();
  expect(
    fetchMock.mock.calls.filter(
      ([input, init]) =>
        String(input).startsWith(`/api/v1/projects/${projectId}/ai/proposals/`) &&
        init?.method !== 'POST',
    ).length,
  ).toBeGreaterThan(1);
}, 6_000);
