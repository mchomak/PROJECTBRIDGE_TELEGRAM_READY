import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createProjectInvitation,
  invitationQueryKeys,
  revokeProjectInvitation,
  type Invitation,
  type InvitationCreate,
} from '../../../entities/invitation';

export function useCreateProjectInvitation(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<Invitation, Error, InvitationCreate>({
    mutationFn: (data) => createProjectInvitation(projectId, data),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: invitationQueryKeys.project(projectId),
      });
    },
  });
}

export function useRevokeProjectInvitation(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<Invitation, Error, string>({
    mutationFn: (invitationId) => revokeProjectInvitation(projectId, invitationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: invitationQueryKeys.project(projectId),
      });
    },
  });
}
