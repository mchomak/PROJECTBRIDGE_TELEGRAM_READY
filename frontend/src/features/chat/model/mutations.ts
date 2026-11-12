import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  chatQueryKeys,
  createProjectMessage,
  type ChatMessage,
  type ChatMessageCreate,
} from '../../../entities/chat';

export function useSendProjectMessage(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<ChatMessage, Error, ChatMessageCreate>({
    mutationFn: (data) => createProjectMessage(projectId, data),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: chatQueryKeys.history(projectId) });
    },
  });
}
