import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  saveSpecification,
  specificationQueryKeys,
  startSpecificationGeneration,
} from '../../../entities/specification';

export function useSaveSpecification(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ content, version }: { content: string; version: number }) =>
      saveSpecification(projectId, content, version),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: specificationQueryKeys.detail(projectId) });
    },
  });
}

export function useStartSpecificationGeneration(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (idempotencyKey: string) => startSpecificationGeneration(projectId, idempotencyKey),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: specificationQueryKeys.detail(projectId) });
    },
  });
}
