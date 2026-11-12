import { apiJson } from '../../../shared/api';
import type {
  EvidenceOption,
  ProjectStateAggregate,
  ProjectStateCollection,
  ProjectStateCreateByCollection,
  ProjectStatePageByCollection,
  ProjectStatePatchByKind,
  ProjectStateRecordKind,
  ProjectStateResponseByCollection,
  ProjectStateResponseByKind,
} from '../model/types';

type CollectionResponse<K extends ProjectStateCollection> = ProjectStatePageByCollection[K];
type ProjectStatePage<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

const recordPaths: Record<ProjectStateRecordKind, string> = {
  stage: 'stages',
  requirement: 'requirements',
  task: 'tasks',
  'open-question': 'open-questions',
  conflict: 'conflicts',
};

function projectPath(projectId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}`;
}

function jsonBody(method: 'POST' | 'PATCH', body: unknown) {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

async function getAllPages<Page extends ProjectStatePage<unknown>>(url: string): Promise<Page> {
  const firstPage = await apiJson<Page>(url);
  const results = [...firstPage.results];
  let next = firstPage.next;

  while (next) {
    const page = await apiJson<ProjectStatePage<unknown>>(next);
    results.push(...page.results);
    next = page.next;
  }

  return { ...firstPage, next: null, results } as Page;
}

export function getProjectStateAggregate(projectId: string): Promise<ProjectStateAggregate> {
  return apiJson<ProjectStateAggregate>(`${projectPath(projectId)}/state/`);
}

export function getProjectStateCollection<K extends ProjectStateCollection>(
  projectId: string,
  collection: K,
  page = 1,
): Promise<CollectionResponse<K>> {
  const params = new URLSearchParams({ page: String(page), page_size: '100' });
  return getAllPages<CollectionResponse<K>>(
    `${projectPath(projectId)}/${collection}/?${params.toString()}`,
  );
}

export function getProjectStateEvidenceOptions(projectId: string): Promise<{
  count: number;
  next: string | null;
  previous: string | null;
  results: EvidenceOption[];
}> {
  return getAllPages<ProjectStatePage<EvidenceOption>>(
    `${projectPath(projectId)}/evidence-options/?page_size=100`,
  );
}

export function createProjectStateRecord<K extends ProjectStateCollection>(
  projectId: string,
  collection: K,
  data: ProjectStateCreateByCollection[K],
): Promise<ProjectStateResponseByCollection[K]> {
  return apiJson<ProjectStateResponseByCollection[K]>(
    `${projectPath(projectId)}/${collection}/`,
    jsonBody('POST', data),
  );
}

export function updateProjectStateRecord<K extends ProjectStateRecordKind>(
  kind: K,
  recordId: string,
  changes: ProjectStatePatchByKind[K],
): Promise<ProjectStateResponseByKind[K]> {
  return apiJson<ProjectStateResponseByKind[K]>(
    `/api/v1/${recordPaths[kind]}/${encodeURIComponent(recordId)}/`,
    jsonBody('PATCH', changes),
  );
}
