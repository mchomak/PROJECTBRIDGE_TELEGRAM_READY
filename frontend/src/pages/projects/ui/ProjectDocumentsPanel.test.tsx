import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import type { ProjectDocument } from '../../../entities/documents';
import { ProjectDocumentsPanel } from './ProjectDocumentsPanel';

const projectId = 'ab0c186a-0675-4819-a294-fd69f2f01cf6';
const executorId = '9aaf57c9-8f43-46ea-9306-ea687cab9f6c';

function makeDocument(overrides: Partial<ProjectDocument> = {}): ProjectDocument {
  return {
    id: 'd6e88a87-43b0-4e18-891e-3f03238da9c5',
    project_id: projectId,
    uploaded_by_id: executorId,
    original_filename: 'scope.txt',
    mime_type: 'text/plain',
    file_size: 18,
    checksum_sha256: 'd'.repeat(64),
    lifecycle_status: 'active',
    processing_status: 'queued',
    processing_dispatch_error_code: '',
    created_at: '2026-11-12T12:00:00Z',
    archived_at: null,
    deleted_at: null,
    lifecycle_request: null,
    ...overrides,
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

class FakeXmlHttpRequest {
  static requests: FakeXmlHttpRequest[] = [];

  readonly upload: { onprogress: ((event: ProgressEvent) => void) | null } = {
    onprogress: null,
  };
  readonly headers = new Map<string, string>();
  method = '';
  url = '';
  withCredentials = false;
  status = 0;
  responseText = '';
  body: XMLHttpRequestBodyInit | Document | null = null;
  onload: ((event: ProgressEvent) => void) | null = null;
  onerror: ((event: ProgressEvent) => void) | null = null;
  onabort: ((event: ProgressEvent) => void) | null = null;

  constructor() {
    FakeXmlHttpRequest.requests.push(this);
  }

  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }

  setRequestHeader(name: string, value: string) {
    this.headers.set(name, value);
  }

  send(body: XMLHttpRequestBodyInit | Document | null) {
    this.body = body;
  }

  reportProgress(loaded: number, total: number) {
    this.upload.onprogress?.({
      lengthComputable: true,
      loaded,
      total,
    } as ProgressEvent);
  }

  finish(status: number, payload: unknown) {
    this.status = status;
    this.responseText = JSON.stringify(payload);
    this.onload?.({} as ProgressEvent);
  }
}

function renderPanel(currentUserId = executorId) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectDocumentsPanel
        canManageLifecycle
        canUpload
        currentUserId={currentUserId}
        projectId={projectId}
      />
    </QueryClientProvider>,
  );
}

function setCsrfCookie() {
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    value: 'csrftoken=csrf-token-value',
  });
}

afterEach(() => {
  FakeXmlHttpRequest.requests = [];
  vi.unstubAllGlobals();
});

test('validates file extension and retains a failed upload for retry with progress', async () => {
  let documents = [makeDocument()];
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') return jsonResponse({ csrf_token: 'csrf-token-value' });
    if (path.startsWith(`/api/v1/projects/${projectId}/documents/`)) {
      return jsonResponse({
        count: documents.length,
        next: null,
        previous: null,
        results: documents,
      });
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('XMLHttpRequest', FakeXmlHttpRequest as unknown as typeof XMLHttpRequest);

  renderPanel();
  expect(await screen.findByText('scope.txt')).toBeTruthy();
  expect(screen.getByText('Queued · not searchable')).toBeTruthy();

  const input = screen.getByLabelText('Choose a document') as HTMLInputElement;
  fireEvent.change(input, {
    target: { files: [new File(['no'], 'notes.exe', { type: 'text/plain' })] },
  });
  expect(await screen.findByText('Choose a PDF, DOCX, TXT, or Markdown file.')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Upload document' }).hasAttribute('disabled')).toBe(
    true,
  );
  expect(FakeXmlHttpRequest.requests).toHaveLength(0);

  fireEvent.change(input, {
    target: { files: [new File(['scope'], 'scope.md', { type: 'application/pdf' })] },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Upload document' }));
  await waitFor(() => expect(FakeXmlHttpRequest.requests).toHaveLength(1));

  const firstAttempt = FakeXmlHttpRequest.requests[0];
  expect(firstAttempt.method).toBe('POST');
  expect(firstAttempt.url).toBe(`/api/v1/projects/${projectId}/documents/`);
  expect(firstAttempt.withCredentials).toBe(true);
  expect(firstAttempt.headers.get('X-CSRFToken')).toBe('csrf-token-value');
  expect(firstAttempt.body).toBeInstanceOf(FormData);
  firstAttempt.reportProgress(40, 100);
  expect(await screen.findByText('40% uploaded')).toBeTruthy();
  firstAttempt.finish(503, {
    code: 'service_unavailable',
    detail: 'Temporary upload failure.',
    errors: null,
    request_id: '2f99e906-7337-4e2d-a46f-f20908f3dd4b',
  });

  expect(await screen.findByText('Temporary upload failure.')).toBeTruthy();
  expect((screen.getByLabelText('Choose a document') as HTMLInputElement).files?.[0]?.name).toBe(
    'scope.md',
  );

  fireEvent.click(screen.getByRole('button', { name: 'Retry upload' }));
  await waitFor(() => expect(FakeXmlHttpRequest.requests).toHaveLength(2));
  const retry = FakeXmlHttpRequest.requests[1];
  retry.reportProgress(80, 100);
  expect(await screen.findByText('80% uploaded')).toBeTruthy();

  const uploaded = makeDocument({
    id: 'a0e9c201-25a3-4823-a8b9-e89d42688503',
    original_filename: 'scope.md',
    mime_type: 'text/markdown',
    file_size: 5,
  });
  retry.finish(201, uploaded);
  documents = [uploaded, ...documents];

  expect(await screen.findByText('scope.md uploaded. Processing is queued.')).toBeTruthy();
  expect(await screen.findAllByText('Queued · not searchable')).toHaveLength(2);
  expect(await screen.findByText('scope.md')).toBeTruthy();
});

test.each(['queue_unavailable', 'worker_backlog'])(
  'queued documents explain %s dispatch delay and clear the warning after recovery',
  async (warningCode) => {
    setCsrfCookie();
    let documentReads = 0;
    const delayed = makeDocument({
      processing_status: 'queued',
      processing_dispatch_error_code: warningCode,
    });
    const ready = makeDocument({
      processing_status: 'ready',
      processing_dispatch_error_code: '',
    });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === '/api/v1/auth/csrf/') return jsonResponse({ csrf_token: 'csrf-token-value' });
      if (path.startsWith(`/api/v1/projects/${projectId}/documents/`)) {
        documentReads += 1;
        const document = documentReads === 1 ? delayed : ready;
        return jsonResponse({ count: 1, next: null, previous: null, results: [document] });
      }
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    renderPanel();
    const warning =
      'The upload is saved and waiting for processing. The system will keep retrying; processing has not started.';
    expect(await screen.findByText(warning)).toBeTruthy();
    expect(screen.getByText('Waiting for processing · retrying')).toBeTruthy();
    expect(await screen.findByText('Ready to search', {}, { timeout: 6_000 })).toBeTruthy();
    await waitFor(() => expect(screen.queryByText(warning)).toBeNull());
    expect(documentReads).toBeGreaterThan(1);
  },
  8_000,
);

test('archive request explains both-party consent and keeps a retry after a temporary failure', async () => {
  setCsrfCookie();
  let requestAttempts = 0;
  let document = makeDocument();
  const lifecycleRequest = {
    id: '58e6c2b0-f4ab-46f0-9cbb-8ad4d6ed2d88',
    document_id: document.id,
    action: 'archive',
    initiated_by_id: executorId,
    status: 'pending',
    approvals: [
      {
        user_id: executorId,
        decision: 'approved',
        decided_at: '2026-11-12T12:00:00Z',
      },
    ],
    viewer_decision: 'approved',
    deletion_after: null,
    created_at: '2026-11-12T12:00:00Z',
    completed_at: null,
  } satisfies NonNullable<ProjectDocument['lifecycle_request']>;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') return jsonResponse({ csrf_token: 'csrf-token-value' });
    if (path.startsWith(`/api/v1/projects/${projectId}/documents/`)) {
      return jsonResponse({ count: 1, next: null, previous: null, results: [document] });
    }
    if (path === `/api/v1/documents/${document.id}/lifecycle-requests/`) {
      expect(init?.method).toBe('POST');
      expect(JSON.parse(String(init?.body))).toEqual({ action: 'archive' });
      requestAttempts += 1;
      if (requestAttempts === 1) {
        return jsonResponse(
          {
            code: 'service_unavailable',
            detail: 'The archive request could not be sent.',
            errors: null,
            request_id: '2f99e906-7337-4e2d-a46f-f20908f3dd4b',
          },
          503,
        );
      }
      document = makeDocument({
        lifecycle_status: 'archive_pending',
        lifecycle_request: lifecycleRequest,
      });
      return jsonResponse(lifecycleRequest, 201);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  renderPanel();
  expect(await screen.findByText('scope.txt')).toBeTruthy();

  fireEvent.click(screen.getByRole('button', { name: 'Request archive' }));
  expect(await screen.findByText('The archive request could not be sent.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Retry archive request' }));

  expect(await screen.findByText('Archive consent: 1 of 2 participants.')).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Approve archive' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Reject archive' })).toBeNull();
  expect(requestAttempts).toBe(2);
});

test('refreshes lifecycle state when the server commits but the response is lost', async () => {
  setCsrfCookie();
  let document = makeDocument();
  const lifecycleRequest = {
    id: '58e6c2b0-f4ab-46f0-9cbb-8ad4d6ed2d88',
    document_id: document.id,
    action: 'archive',
    initiated_by_id: executorId,
    status: 'pending',
    approvals: [
      {
        user_id: executorId,
        decision: 'approved',
        decided_at: '2026-11-12T12:00:00Z',
      },
    ],
    viewer_decision: 'approved',
    deletion_after: null,
    created_at: '2026-11-12T12:00:00Z',
    completed_at: null,
  } satisfies NonNullable<ProjectDocument['lifecycle_request']>;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') return jsonResponse({ csrf_token: 'csrf-token-value' });
    if (path.startsWith(`/api/v1/projects/${projectId}/documents/`)) {
      return jsonResponse({ count: 1, next: null, previous: null, results: [document] });
    }
    if (path === `/api/v1/documents/${document.id}/lifecycle-requests/`) {
      document = makeDocument({
        lifecycle_status: 'archive_pending',
        lifecycle_request: lifecycleRequest,
      });
      throw new TypeError('Network response was lost.');
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  renderPanel();
  expect(await screen.findByText('scope.txt')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Request archive' }));

  expect(await screen.findByText('Network response was lost.')).toBeTruthy();
  expect(await screen.findByText('Archive consent: 1 of 2 participants.')).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Request archive' })).toBeNull();
});

test('the other participant can approve an archive after seeing the pending consent count', async () => {
  setCsrfCookie();
  const requestId = '58e6c2b0-f4ab-46f0-9cbb-8ad4d6ed2d88';
  const customerId = '82043502-cdad-431f-9657-c4c8780ffcb7';
  const pendingRequest = {
    id: requestId,
    document_id: makeDocument().id,
    action: 'archive',
    initiated_by_id: executorId,
    status: 'pending',
    approvals: [
      {
        user_id: executorId,
        decision: 'approved',
        decided_at: '2026-11-12T12:00:00Z',
      },
    ],
    viewer_decision: null,
    deletion_after: null,
    created_at: '2026-11-12T12:00:00Z',
    completed_at: null,
  } satisfies NonNullable<ProjectDocument['lifecycle_request']>;
  let document: ProjectDocument | null = makeDocument({
    lifecycle_status: 'archive_pending',
    lifecycle_request: pendingRequest,
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') return jsonResponse({ csrf_token: 'csrf-token-value' });
    if (path.startsWith(`/api/v1/projects/${projectId}/documents/`)) {
      return jsonResponse({
        count: document ? 1 : 0,
        next: null,
        previous: null,
        results: document ? [document] : [],
      });
    }
    if (path === `/api/v1/document-lifecycle-requests/${requestId}/approve/`) {
      expect(init?.method).toBe('POST');
      const approved = {
        ...pendingRequest,
        status: 'approved',
        approvals: [
          ...pendingRequest.approvals,
          {
            user_id: customerId,
            decision: 'approved',
            decided_at: '2026-11-12T12:02:00Z',
          },
        ],
        viewer_decision: 'approved',
      } satisfies NonNullable<ProjectDocument['lifecycle_request']>;
      document = null;
      return jsonResponse(approved);
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  renderPanel(customerId);
  expect(await screen.findByText('Archive consent: 1 of 2 participants.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Approve archive' }));

  expect(await screen.findByText('No shared documents yet.')).toBeTruthy();
  expect(screen.queryByText('scope.txt')).toBeNull();
});

test('deletion view shows a cancellation countdown and returns a cancelled document to archive', async () => {
  setCsrfCookie();
  const customerId = '82043502-cdad-431f-9657-c4c8780ffcb7';
  const requestId = '58e6c2b0-f4ab-46f0-9cbb-8ad4d6ed2d88';
  const deletionAfter = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();
  const request = {
    id: requestId,
    document_id: makeDocument().id,
    action: 'permanent_delete',
    initiated_by_id: executorId,
    status: 'approved',
    approvals: [
      {
        user_id: executorId,
        decision: 'approved',
        decided_at: '2026-11-12T12:00:00Z',
      },
      {
        user_id: customerId,
        decision: 'approved',
        decided_at: '2026-11-12T12:02:00Z',
      },
    ],
    viewer_decision: 'approved',
    deletion_after: deletionAfter,
    created_at: '2026-11-12T12:00:00Z',
    completed_at: null,
  } satisfies NonNullable<ProjectDocument['lifecycle_request']>;
  let documents: ProjectDocument[] = [
    makeDocument({ lifecycle_status: 'deletion_pending', lifecycle_request: request }),
  ];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === '/api/v1/auth/csrf/') return jsonResponse({ csrf_token: 'csrf-token-value' });
    if (path.startsWith(`/api/v1/projects/${projectId}/documents/`)) {
      expect(path).toContain('status=deletion_pending');
      return jsonResponse({
        count: documents.length,
        next: null,
        previous: null,
        results: documents,
      });
    }
    if (path === `/api/v1/document-lifecycle-requests/${requestId}/cancel/`) {
      expect(init?.method).toBe('POST');
      documents = [];
      return jsonResponse({ ...request, status: 'cancelled' });
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal('fetch', fetchMock);

  renderPanel(customerId);
  fireEvent.click(screen.getByRole('button', { name: 'Deletion pending' }));

  expect(await screen.findByText(/\d+d \d+h \d+m until permanent deletion\./)).toBeTruthy();
  expect(screen.getByText(/Encrypted backups may retain a copy/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Cancel permanent deletion' }));

  expect(await screen.findByText('No shared documents yet.')).toBeTruthy();
  expect(screen.queryByText('scope.txt')).toBeNull();
});
