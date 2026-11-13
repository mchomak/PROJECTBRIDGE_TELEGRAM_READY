import { apiJson } from '../../../shared/api';
import type { components } from '../../../shared/api/generated/schema';

export type AIAnalysisRequest = components['schemas']['AIAnalysisRequest'];
export type AIAnalysisRequestPage = components['schemas']['AIAnalysisRequestPage'];
export type AIProposal = components['schemas']['AIProposal'];
export type AIProposalPage = components['schemas']['AIProposalPage'];

type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

async function getAllPages<T>(url: string): Promise<T[]> {
  const firstPage = await apiJson<Page<T>>(url);
  const results = [...firstPage.results];
  let next = firstPage.next;
  while (next) {
    const page = await apiJson<Page<T>>(next);
    results.push(...page.results);
    next = page.next;
  }
  return results;
}

function projectPath(projectId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/ai`;
}

function jsonPost(body: unknown = {}) {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

export function getAIAnalysisRequests(projectId: string): Promise<AIAnalysisRequest[]> {
  return getAllPages<AIAnalysisRequest>(`${projectPath(projectId)}/analyses/?page_size=100`);
}

export function getAIAnalysisRequest(
  projectId: string,
  requestId: string,
): Promise<AIAnalysisRequest> {
  return apiJson<AIAnalysisRequest>(
    `${projectPath(projectId)}/analyses/${encodeURIComponent(requestId)}/`,
  );
}

export function startManualAIAnalysis(
  projectId: string,
  idempotencyKey: string,
): Promise<AIAnalysisRequest> {
  return apiJson<AIAnalysisRequest>(`${projectPath(projectId)}/analyses/`, {
    ...jsonPost(),
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
  });
}

export function getAIProposals(projectId: string): Promise<AIProposal[]> {
  return getAllPages<AIProposal>(`${projectPath(projectId)}/proposals/?page_size=100`);
}

export function acceptAIProposal(proposalId: string): Promise<AIProposal> {
  return apiJson<AIProposal>(
    `/api/v1/ai/proposals/${encodeURIComponent(proposalId)}/accept/`,
    jsonPost(),
  );
}

export function rejectAIProposal(proposalId: string): Promise<AIProposal> {
  return apiJson<AIProposal>(
    `/api/v1/ai/proposals/${encodeURIComponent(proposalId)}/reject/`,
    jsonPost(),
  );
}

export function applyEditedAIProposal(
  proposalId: string,
  finalPayload: Record<string, unknown>,
): Promise<AIProposal> {
  return apiJson<AIProposal>(
    `/api/v1/ai/proposals/${encodeURIComponent(proposalId)}/apply-edited/`,
    jsonPost({ final_payload: finalPayload }),
  );
}
