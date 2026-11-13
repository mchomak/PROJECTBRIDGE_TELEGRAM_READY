import { apiJson } from '../../../shared/api';
import type { Specification, SpecificationGeneration } from '../model/types';

function projectPath(projectId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/specification`;
}

export function getSpecification(projectId: string): Promise<Specification> {
  return apiJson<Specification>(`${projectPath(projectId)}/`);
}

export function saveSpecification(
  projectId: string,
  content: string,
  version: number,
): Promise<Specification> {
  return apiJson<Specification>(`${projectPath(projectId)}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, version }),
  });
}

export function startSpecificationGeneration(
  projectId: string,
  idempotencyKey: string,
): Promise<SpecificationGeneration> {
  return apiJson<SpecificationGeneration>(`${projectPath(projectId)}/generate/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({}),
  });
}
