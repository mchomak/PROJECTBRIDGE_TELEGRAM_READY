import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router';
import { afterEach, expect, test, vi } from 'vitest';
import type { User } from '../../../entities/user';
import type { Project, ProjectMember, ProjectPassport } from '../../../entities/project';
import type { Invitation, InvitationStatus } from '../../../entities/invitation';
import { projectQueryKeys } from '../../../entities/project';
import { ProjectCreatePage } from './ProjectCreatePage';
import { ProjectListPage } from './ProjectListPage';
import { ProjectOverviewPage } from './ProjectOverviewPage';

const projectId = 'ab0c186a-0675-4819-a294-fd69f2f01cf6';
const executorId = '9aaf57c9-8f43-46ea-9306-ea687cab9f6c';
const customerId = '82043502-cdad-431f-9657-c4c8780ffcb7';
const user: User = {
  id: executorId,
  email: 'executor@example.com',
  first_name: 'Alex',
  last_name: 'Stone',
  email_verified: true,
  email_verified_at: '2026-11-11T00:00:00Z',
};

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: projectId,
    name: 'Client portal',
    description: 'A portal for customers',
    project_type: 'website',
    status: 'active',
    created_at: '2026-11-11T00:00:00Z',
    updated_at: '2026-11-11T00:00:00Z',
    completed_at: null,
    archived_at: null,
    ...overrides,
  };
}

function makeMember(role: ProjectMember['role'] = 'executor'): ProjectMember {
  return {
    id: '5def8971-65cb-4622-8dc7-7ee4e031dc72',
    user_id: role === 'executor' ? executorId : customerId,
    role,
    joined_at: '2026-11-11T00:00:00Z',
    first_name: role === 'executor' ? 'Alex' : 'Morgan',
    last_name: role === 'executor' ? 'Stone' : 'Lee',
  };
}

function makePassport(overrides: Partial<ProjectPassport> = {}): ProjectPassport {
  return {
    id: 'b5b97426-c477-4585-a8ea-46fce163f65b',
    project_id: projectId,
    goal: 'Launch a customer portal',
    target_audience: 'Existing customers',
    expected_result: 'Customers can manage requests',
    functional_scope: ['accounts', 'requests'],
    integrations: { billing: 'Stripe' },
    constraints: ['Keep the current identity provider'],
    deadline: null,
    budget_min: null,
    budget_max: null,
    currency: null,
    additional_data: { source: 'discovery' },
    version: 1,
    created_at: '2026-11-11T00:00:00Z',
    updated_at: '2026-11-11T00:00:00Z',
    ...overrides,
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function setCsrfCookie() {
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=csrf-token-value',
  });
}

function renderProjectPage(
  path: string,
  page = 'overview',
  currentUser = user,
  options: { mockEmptyInvitations?: boolean } = {},
) {
  if (options.mockEmptyInvitations !== false) {
    const baseFetch = globalThis.fetch;
    vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
      if ((!init?.method || init.method === 'GET') && String(input).includes('/invitations/?')) {
        return jsonResponse({ count: 0, next: null, previous: null, results: [] });
      }
      return baseFetch(input, init);
    });
  }

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const rendered = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<Outlet context={currentUser} />}>
            <Route path="/app/projects" element={<ProjectListPage />} />
            <Route path="/app/projects/archive" element={<ProjectListPage archived />} />
            <Route path="/app/projects/new" element={<ProjectCreatePage />} />
            <Route
              path="/app/projects/:projectId"
              element={
                page === 'create' ? <h1>Created project overview</h1> : <ProjectOverviewPage />
              }
            />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...rendered, queryClient };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test('project list paginates and requests the next page', async () => {
  const firstProject = makeProject();
  const secondProject = makeProject({
    id: '0d21cbc1-548b-4243-8180-cee9a45ebfda',
    name: 'Mobile app',
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input) === '/api/v1/projects/?page=1') {
      return jsonResponse({
        count: 2,
        next: 'http://test/api/v1/projects/?page=2',
        previous: null,
        results: [firstProject],
      });
    }
    if (String(input) === '/api/v1/projects/?page=2') {
      return jsonResponse({
        count: 2,
        next: null,
        previous: 'http://test/api/v1/projects/?page=1',
        results: [secondProject],
      });
    }
    throw new Error(`Unexpected request: ${String(input)}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  renderProjectPage('/app/projects', 'list');

  expect(await screen.findByRole('link', { name: /Client portal/ })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Next' }));
  expect(await screen.findByRole('link', { name: /Mobile app/ })).toBeTruthy();
  expect(fetchMock.mock.calls.map(([input]) => String(input))).toContain(
    '/api/v1/projects/?page=2',
  );
  expect(screen.getByText('Page 2')).toBeTruthy();
});

test('executor manages invitation status and can recover from a server validation error', async () => {
  setCsrfCookie();
  const invitationRows: Array<Record<string, unknown>> = [
    {
      id: '18b962e1-5084-47e3-b32a-08bdb01af37f',
      project_id: projectId,
      invited_email: 'pending@example.com',
      status: 'pending',
      expires_at: '2026-11-19T12:00:00Z',
      accepted_at: null,
      revoked_at: null,
      created_at: '2026-11-12T12:00:00Z',
    },
    {
      id: 'd6e88a87-43b0-4e18-891e-3f03238da9c5',
      project_id: projectId,
      invited_email: 'expired@example.com',
      status: 'expired',
      expires_at: '2026-11-11T12:00:00Z',
      accepted_at: null,
      revoked_at: null,
      created_at: '2026-11-04T12:00:00Z',
    },
    {
      id: '3e2a0ee3-7df1-4d10-8a74-5720e5d95ca1',
      project_id: projectId,
      invited_email: 'accepted@example.com',
      status: 'accepted',
      expires_at: '2026-11-11T12:00:00Z',
      accepted_at: '2026-11-10T12:00:00Z',
      revoked_at: null,
      created_at: '2026-11-03T12:00:00Z',
    },
    {
      id: 'ad74e8a1-782e-45c5-b891-df7c39969468',
      project_id: projectId,
      invited_email: 'revoked@example.com',
      status: 'revoked',
      expires_at: '2026-11-11T12:00:00Z',
      accepted_at: null,
      revoked_at: '2026-11-05T12:00:00Z',
      created_at: '2026-11-02T12:00:00Z',
    },
  ];
  let rejectFirstCreate = true;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === `/api/v1/projects/${projectId}/`) return jsonResponse(makeProject());
    if (path === `/api/v1/projects/${projectId}/members/`)
      return jsonResponse([makeMember('executor')]);
    if (path === `/api/v1/projects/${projectId}/passport/`) return jsonResponse(makePassport());
    if (path.startsWith(`/api/v1/projects/${projectId}/invitations/`)) {
      if (!init?.method || init.method === 'GET') {
        return jsonResponse({
          count: invitationRows.length,
          next: null,
          previous: null,
          results: invitationRows,
        });
      }
      if (path === `/api/v1/projects/${projectId}/invitations/`) {
        if (rejectFirstCreate) {
          rejectFirstCreate = false;
          return jsonResponse(
            {
              code: 'validation_error',
              detail: 'Please correct the highlighted fields.',
              errors: { invited_email: ['This email already has an active invitation.'] },
              request_id: 'f37c2398-a0ce-45e6-8b65-a6eea790fed1',
            },
            400,
          );
        }
        const created = {
          id: '0d5b3ee2-4855-4335-a805-ae4f904344f8',
          project_id: projectId,
          invited_email: 'new@example.com',
          status: 'pending',
          expires_at: '2026-11-19T12:00:00Z',
          accepted_at: null,
          revoked_at: null,
          created_at: '2026-11-12T12:01:00Z',
        };
        invitationRows.unshift(created);
        return jsonResponse(created, 201);
      }
      const pendingId = '18b962e1-5084-47e3-b32a-08bdb01af37f';
      expect(path).toBe(`/api/v1/projects/${projectId}/invitations/${pendingId}/revoke/`);
      const pending = invitationRows.find((row) => row.id === pendingId);
      if (pending) pending.status = 'revoked';
      return jsonResponse(pending);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  renderProjectPage(`/app/projects/${projectId}`, 'overview', user, {
    mockEmptyInvitations: false,
  });

  expect(await screen.findByRole('heading', { name: 'Project invitations' })).toBeTruthy();
  expect(await screen.findByText('pending@example.com')).toBeTruthy();
  for (const [email, label] of [
    ['pending@example.com', 'Pending'],
    ['expired@example.com', 'Expired'],
    ['accepted@example.com', 'Accepted'],
    ['revoked@example.com', 'Revoked'],
  ]) {
    expect(screen.getByText(email)).toBeTruthy();
    expect(screen.getByText(label, { exact: true })).toBeTruthy();
  }

  const emailInput = screen.getByLabelText('Customer email') as HTMLInputElement;
  fireEvent.change(emailInput, { target: { value: 'new@example.com' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send invitation' }));
  expect(await screen.findByText('This email already has an active invitation.')).toBeTruthy();
  expect(emailInput.value).toBe('new@example.com');

  fireEvent.click(screen.getByRole('button', { name: 'Send invitation' }));
  expect(await screen.findByText('Invitation sent to new@example.com.')).toBeTruthy();
  expect(await screen.findByText('new@example.com')).toBeTruthy();

  fireEvent.click(screen.getByRole('button', { name: 'Revoke invitation to pending@example.com' }));
  expect(await screen.findByText('Invitation to pending@example.com revoked.')).toBeTruthy();
  expect(screen.getAllByText('Revoked', { exact: true })).toHaveLength(2);
});

test('executor can reach and revoke an older invitation on the next page', async () => {
  setCsrfCookie();
  const newest = {
    id: '18b962e1-5084-47e3-b32a-08bdb01af37f',
    project_id: projectId,
    invited_email: 'newest@example.com',
    status: 'pending',
    expires_at: '2026-11-19T12:00:00Z',
    accepted_at: null,
    revoked_at: null,
    created_at: '2026-11-12T12:00:00Z',
  };
  const older: Omit<Invitation, 'status' | 'revoked_at'> & {
    status: InvitationStatus;
    revoked_at: string | null;
  } = {
    id: 'd6e88a87-43b0-4e18-891e-3f03238da9c5',
    project_id: projectId,
    invited_email: 'older@example.com',
    status: 'pending',
    expires_at: '2026-11-19T12:00:00Z',
    accepted_at: null,
    revoked_at: null,
    created_at: '2026-11-04T12:00:00Z',
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === `/api/v1/projects/${projectId}/`) return jsonResponse(makeProject());
    if (path === `/api/v1/projects/${projectId}/members/`)
      return jsonResponse([makeMember('executor')]);
    if (path === `/api/v1/projects/${projectId}/passport/`) return jsonResponse(makePassport());
    if (path.startsWith(`/api/v1/projects/${projectId}/invitations/?`)) {
      if (path.includes('page=1')) {
        return jsonResponse({
          count: 2,
          next: `http://test/api/v1/projects/${projectId}/invitations/?page=2&page_size=100`,
          previous: null,
          results: [newest],
        });
      }
      expect(path).toContain('page=2&page_size=100');
      return jsonResponse({
        count: 2,
        next: null,
        previous: `http://test/api/v1/projects/${projectId}/invitations/?page=1&page_size=100`,
        results: [older],
      });
    }
    if (path === `/api/v1/projects/${projectId}/invitations/${older.id}/revoke/`) {
      older.status = 'revoked';
      older.revoked_at = '2026-11-12T12:02:00Z';
      return jsonResponse(older);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  renderProjectPage(`/app/projects/${projectId}`, 'overview', user, {
    mockEmptyInvitations: false,
  });

  expect(await screen.findByText('newest@example.com')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Next invitations' }));
  expect(await screen.findByText('older@example.com')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Revoke invitation to older@example.com' }));
  expect(await screen.findByText('Invitation to older@example.com revoked.')).toBeTruthy();
  expect(screen.getByText('Revoked', { exact: true })).toBeTruthy();
});

test('archive list filters for archived projects and has a distinct empty state', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    expect(String(input)).toBe('/api/v1/projects/?page=1&status=archived');
    return jsonResponse({ count: 0, next: null, previous: null, results: [] });
  });
  vi.stubGlobal('fetch', fetchMock);
  renderProjectPage('/app/projects/archive', 'archive');

  expect(await screen.findByRole('heading', { name: 'No archived projects' })).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Back to projects' })).toBeTruthy();
});

test('project list keeps a retry action after a temporary server failure', async () => {
  let attempts = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    expect(String(input)).toBe('/api/v1/projects/?page=1');
    attempts += 1;
    if (attempts <= 3) {
      return jsonResponse(
        {
          code: 'service_unavailable',
          detail: 'Projects are temporarily unavailable.',
          errors: null,
          request_id: '2f99e906-7337-4e2d-a46f-f20908f3dd4b',
        },
        503,
      );
    }
    return jsonResponse({ count: 1, next: null, previous: null, results: [makeProject()] });
  });
  vi.stubGlobal('fetch', fetchMock);
  renderProjectPage('/app/projects', 'list');

  expect(await screen.findByText('Projects are temporarily unavailable.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
  expect(await screen.findByRole('link', { name: /Client portal/ })).toBeTruthy();
  expect(attempts).toBe(4);
});

test('project creation validates input, offers exactly four types, and retains values after API errors', async () => {
  setCsrfCookie();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    expect(String(input)).toBe('/api/v1/projects/');
    expect(init?.method).toBe('POST');
    expect(new Headers(init?.headers).get('X-CSRFToken')).toBe('csrf-token-value');
    return jsonResponse(
      {
        code: 'validation_error',
        detail: 'Please correct the highlighted fields.',
        errors: { name: ['A project with this name already exists.'] },
        request_id: 'b56ce76f-589a-429c-a17c-e0a2495c917b',
      },
      400,
    );
  });
  vi.stubGlobal('fetch', fetchMock);
  renderProjectPage('/app/projects/new', 'create');

  const typeSelect = screen.getByLabelText('Project type') as HTMLSelectElement;
  expect(Array.from(typeSelect.options).map((option) => option.value)).toEqual([
    '',
    'website',
    'telegram_bot',
    'automation',
    'other',
  ]);
  fireEvent.click(screen.getByRole('button', { name: 'Create project' }));
  expect(await screen.findByText('Enter a project name.')).toBeTruthy();
  expect(fetchMock).not.toHaveBeenCalled();

  fireEvent.change(screen.getByLabelText('Project name'), { target: { value: 'Portal refresh' } });
  fireEvent.change(typeSelect, { target: { value: 'telegram_bot' } });
  fireEvent.change(screen.getByLabelText(/Description/), { target: { value: 'A support bot' } });
  fireEvent.click(screen.getByRole('button', { name: 'Create project' }));

  expect(await screen.findByText('A project with this name already exists.')).toBeTruthy();
  expect(screen.getByLabelText('Project name')).toHaveProperty('value', 'Portal refresh');
  expect(screen.getByLabelText('Project type')).toHaveProperty('value', 'telegram_bot');
  expect(screen.getByLabelText(/Description/)).toHaveProperty('value', 'A support bot');
});

test('project creation sends the chosen type and opens the created project', async () => {
  setCsrfCookie();
  const created = makeProject({
    id: 'b9d613cf-1602-4200-a674-b7b1407633b6',
    name: 'Support bot',
    project_type: 'telegram_bot',
    status: 'draft',
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    expect(String(input)).toBe('/api/v1/projects/');
    expect(JSON.parse(String(init?.body))).toEqual({
      name: 'Support bot',
      project_type: 'telegram_bot',
      description: null,
    });
    return jsonResponse(created, 201);
  });
  vi.stubGlobal('fetch', fetchMock);
  renderProjectPage('/app/projects/new', 'create');

  fireEvent.change(screen.getByLabelText('Project name'), { target: { value: ' Support bot ' } });
  fireEvent.change(screen.getByLabelText('Project type'), { target: { value: 'telegram_bot' } });
  fireEvent.click(screen.getByRole('button', { name: 'Create project' }));

  expect(await screen.findByRole('heading', { name: 'Created project overview' })).toBeTruthy();
});

test('customer sees project metadata and the passport as read-only', async () => {
  const customer = { ...user, id: customerId, email: 'customer@example.com' };
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input) === `/api/v1/projects/${projectId}/`) return jsonResponse(makeProject());
    if (String(input) === `/api/v1/projects/${projectId}/members/`)
      return jsonResponse([makeMember('customer')]);
    if (String(input) === `/api/v1/projects/${projectId}/passport/`)
      return jsonResponse(makePassport());
    throw new Error(`Unexpected request: ${String(input)}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  renderProjectPage(`/app/projects/${projectId}`, 'overview', customer);

  expect(await screen.findByRole('heading', { name: 'Client portal' })).toBeTruthy();
  expect(await screen.findByText('Launch a customer portal')).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Open questionnaire' }).getAttribute('href')).toBe(
    `/app/projects/${projectId}/questionnaire`,
  );
  for (const field of [
    'Goal',
    'Target audience',
    'Expected result',
    'Functional scope',
    'Integrations',
    'Constraints',
    'Deadline',
    'Budget minimum',
    'Budget maximum',
    'Currency',
    'Additional data',
  ]) {
    expect(screen.getByText(field)).toBeTruthy();
  }
  expect(screen.queryByRole('button', { name: 'Save project details' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Save passport' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Complete project' })).toBeNull();
  expect(screen.getByText('Read only')).toBeTruthy();
});

test('executor actions follow project status and update the overview after completion', async () => {
  setCsrfCookie();
  let status: Project['status'] = 'active';
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === `/api/v1/projects/${projectId}/`)
      return jsonResponse(makeProject({ status }));
    if (String(input) === `/api/v1/projects/${projectId}/members/`)
      return jsonResponse([makeMember('executor')]);
    if (String(input) === `/api/v1/projects/${projectId}/passport/`)
      return jsonResponse(makePassport());
    if (String(input) === `/api/v1/projects/${projectId}/complete/`) {
      expect(init?.method).toBe('POST');
      status = 'completed';
      return jsonResponse(makeProject({ status }));
    }
    throw new Error(`Unexpected request: ${String(input)}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  renderProjectPage(`/app/projects/${projectId}`);

  expect(await screen.findByRole('button', { name: 'Complete project' })).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Archive project' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Complete project' }));

  expect(await screen.findByRole('button', { name: 'Reopen project' })).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Archive project' })).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Complete project' })).toBeNull();
  expect(screen.getByText('Completed')).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Save passport' })).toBeNull();
});

test.each([
  { status: 'draft' as const, actions: ['Archive project'], canEdit: true },
  { status: 'archived' as const, actions: ['Restore project'], canEdit: false },
])(
  'executor sees status-appropriate actions for $status projects',
  async ({ status, actions, canEdit }) => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) === `/api/v1/projects/${projectId}/`)
        return jsonResponse(makeProject({ status }));
      if (String(input) === `/api/v1/projects/${projectId}/members/`)
        return jsonResponse([makeMember('executor')]);
      if (String(input) === `/api/v1/projects/${projectId}/passport/`)
        return jsonResponse(makePassport());
      throw new Error(`Unexpected request: ${String(input)}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    renderProjectPage(`/app/projects/${projectId}`);

    expect(await screen.findByRole('heading', { name: 'Client portal' })).toBeTruthy();
    for (const action of actions) {
      expect(await screen.findByRole('button', { name: action })).toBeTruthy();
    }
    expect(screen.queryByRole('button', { name: 'Complete project' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Reopen project' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Restore project' }) !== null).toBe(
      actions.includes('Restore project'),
    );
    if (!canEdit) expect(screen.queryByRole('button', { name: 'Save passport' })).toBeNull();
  },
);

test('a background passport refetch cannot upgrade an in-progress draft version', async () => {
  setCsrfCookie();
  let passportReads = 0;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === `/api/v1/projects/${projectId}/`) return jsonResponse(makeProject());
    if (String(input) === `/api/v1/projects/${projectId}/members/`)
      return jsonResponse([makeMember('executor')]);
    if (
      String(input) === `/api/v1/projects/${projectId}/passport/` &&
      (!init?.method || init.method === 'GET')
    ) {
      passportReads += 1;
      return jsonResponse(
        makePassport(
          passportReads === 1 ? {} : { version: 2, goal: 'Updated by another participant' },
        ),
      );
    }
    if (String(input) === `/api/v1/projects/${projectId}/passport/` && init?.method === 'PATCH') {
      const body = JSON.parse(String(init.body)) as Record<string, unknown>;
      expect(body.version).toBe(1);
      expect(body.goal).toBe('My unsaved edit');
      return jsonResponse(
        {
          code: 'stale_passport_version',
          detail: 'The passport changed since it was loaded.',
          errors: null,
          request_id: '2f99e906-7337-4e2d-a46f-f20908f3dd4b',
        },
        409,
      );
    }
    throw new Error(`Unexpected request: ${String(input)}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  const { queryClient } = renderProjectPage(`/app/projects/${projectId}`);

  fireEvent.change(await screen.findByLabelText('Goal'), { target: { value: 'My unsaved edit' } });

  await act(async () => {
    await queryClient.refetchQueries({ queryKey: projectQueryKeys.passport(projectId) });
  });
  expect(passportReads).toBe(2);
  expect(
    queryClient.getQueryData<ProjectPassport>(projectQueryKeys.passport(projectId))?.version,
  ).toBe(2);
  expect(screen.getByLabelText('Goal')).toHaveProperty('value', 'My unsaved edit');
  expect(screen.getByText('Version 1')).toBeTruthy();

  fireEvent.click(screen.getByRole('button', { name: 'Save passport' }));

  expect(
    await screen.findByRole('heading', { name: 'This passport changed on the server' }),
  ).toBeTruthy();
  expect(screen.getByLabelText('Goal')).toHaveProperty('value', 'My unsaved edit');
  expect(passportReads).toBe(2);
  fireEvent.click(screen.getByRole('button', { name: 'Reload latest passport' }));

  await waitFor(() => expect(passportReads).toBe(3));
  expect(screen.getByText('Version 2')).toBeTruthy();
  expect(await screen.findByLabelText('Goal')).toHaveProperty(
    'value',
    'Updated by another participant',
  );
  expect(screen.queryByRole('heading', { name: 'This passport changed on the server' })).toBeNull();
});
