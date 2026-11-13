import { useEffect, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  acceptAIProposal,
  applyEditedAIProposal,
  rejectAIProposal,
  startManualAIAnalysis,
  type AIAnalysisRequest,
} from '../../../entities/ai-analysis';
import { aiAnalysisQueryKeys } from '../../../entities/ai-analysis';

export function useRefreshAIProposalsWhenAnalysisCompletes(
  projectId: string,
  requests: AIAnalysisRequest[] | undefined,
) {
  const queryClient = useQueryClient();
  const previousStatuses = useRef(new Map<string, string>());

  useEffect(() => {
    let analysisCompleted = false;
    for (const request of requests ?? []) {
      const previousStatus = previousStatuses.current.get(request.id);
      if (previousStatus !== 'succeeded' && request.status === 'succeeded') {
        analysisCompleted = true;
      }
      previousStatuses.current.set(request.id, request.status);
    }

    if (analysisCompleted) {
      void queryClient.invalidateQueries({
        queryKey: aiAnalysisQueryKeys.proposals(projectId),
      });
    }
  }, [projectId, queryClient, requests]);
}

export function useStartManualAIAnalysis(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (idempotencyKey: string) => startManualAIAnalysis(projectId, idempotencyKey),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: aiAnalysisQueryKeys.requests(projectId) });
    },
  });
}

export function useAcceptAIProposal(projectId: string, proposalId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => acceptAIProposal(proposalId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: aiAnalysisQueryKeys.proposals(projectId) }),
        queryClient.invalidateQueries({ queryKey: ['project-state', projectId] }),
      ]);
    },
  });
}

export function useApplyEditedAIProposal(projectId: string, proposalId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => applyEditedAIProposal(proposalId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: aiAnalysisQueryKeys.proposals(projectId) }),
        queryClient.invalidateQueries({ queryKey: ['project-state', projectId] }),
      ]);
    },
  });
}

export function useRejectAIProposal(projectId: string, proposalId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => rejectAIProposal(proposalId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: aiAnalysisQueryKeys.proposals(projectId) });
    },
  });
}
