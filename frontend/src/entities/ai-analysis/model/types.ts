import type { components } from '../../../shared/api/generated/schema';

export type AIAnalysisRequest = components['schemas']['AIAnalysisRequest'];
export type AIProposal = components['schemas']['AIProposal'];
export type AIProposalEvidence = components['schemas']['AIProposalEvidence'];
export type AIProposalStatus = components['schemas']['AIProposalStatusEnum'];
export type AIProposalPayload = Record<string, unknown>;

export const aiAnalysisQueryKeys = {
  all: ['ai-analysis'] as const,
  project: (projectId: string) => [...aiAnalysisQueryKeys.all, projectId] as const,
  requests: (projectId: string) => [...aiAnalysisQueryKeys.project(projectId), 'requests'] as const,
  request: (projectId: string, requestId: string) =>
    [...aiAnalysisQueryKeys.requests(projectId), requestId] as const,
  proposals: (projectId: string) =>
    [...aiAnalysisQueryKeys.project(projectId), 'proposals'] as const,
};
