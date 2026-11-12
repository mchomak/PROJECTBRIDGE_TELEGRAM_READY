import { afterEach, expect, test, vi } from 'vitest';
import { getProjectStateCollection, getProjectStateEvidenceOptions } from './projectStateApi';

const projectId = '1e3ae97f-6517-4eac-b81f-b94d34c73f2e';

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test('loads every Project State collection page by following next links', async () => {
  const pageTwo = `/api/v1/projects/${projectId}/stages/?page=2&page_size=100`;
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      jsonResponse({
        count: 2,
        next: pageTwo,
        previous: null,
        results: [{ id: 'stage-first' }],
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        count: 2,
        next: null,
        previous: `/api/v1/projects/${projectId}/stages/?page=1&page_size=100`,
        results: [{ id: 'stage-second' }],
      }),
    );
  vi.stubGlobal('fetch', fetchMock);

  const page = await getProjectStateCollection(projectId, 'stages');

  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(fetchMock).toHaveBeenNthCalledWith(
    1,
    `/api/v1/projects/${projectId}/stages/?page=1&page_size=100`,
    expect.objectContaining({ method: 'GET', credentials: 'same-origin' }),
  );
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    pageTwo,
    expect.objectContaining({ method: 'GET', credentials: 'same-origin' }),
  );
  expect(page.results.map(({ id }) => id)).toEqual(['stage-first', 'stage-second']);
});

test('loads every evidence option page by following next links', async () => {
  const pageTwo = `/api/v1/projects/${projectId}/evidence-options/?page=2&page_size=100`;
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      jsonResponse({
        count: 2,
        next: pageTwo,
        previous: null,
        results: [{ source_id: 'answer-first' }],
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        count: 2,
        next: null,
        previous: `/api/v1/projects/${projectId}/evidence-options/?page=1&page_size=100`,
        results: [{ source_id: 'answer-second' }],
      }),
    );
  vi.stubGlobal('fetch', fetchMock);

  const page = await getProjectStateEvidenceOptions(projectId);

  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(fetchMock).toHaveBeenLastCalledWith(
    pageTwo,
    expect.objectContaining({ method: 'GET', credentials: 'same-origin' }),
  );
  expect(page.results.map(({ source_id }) => source_id)).toEqual(['answer-first', 'answer-second']);
});
