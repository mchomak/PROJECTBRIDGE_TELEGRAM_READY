import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import type { ProjectDocument } from '../../../entities/documents';
import { ProjectDocumentsPanel } from './ProjectDocumentsPanel';

const projectId = 'ab0c186a-0675-4819-a294-fd69f2f01cf6';

function makeDocument(overrides: Partial<ProjectDocument> = {}): ProjectDocument {
  return {
    id: 'd6e88a87-43b0-4e18-891e-3f03238da9c5',
    project_id: projectId,
    uploaded_by_id: '9aaf57c9-8f43-46ea-9306-ea687cab9f6c',
    original_filename: 'scope.txt',
    mime_type: 'text/plain',
    file_size: 18,
    checksum_sha256: 'd'.repeat(64),
    lifecycle_status: 'active',
    processing_status: 'queued',
    created_at: '2026-11-12T12:00:00Z',
    archived_at: null,
    deleted_at: null,
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

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectDocumentsPanel canUpload projectId={projectId} />
    </QueryClientProvider>,
  );
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
  expect(await screen.findAllByText('Queued')).toHaveLength(2);
  expect(await screen.findByText('scope.md')).toBeTruthy();
});
