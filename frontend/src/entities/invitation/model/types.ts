import type { components } from '../../../shared/api/generated/schema';

export type Invitation = components['schemas']['InvitationResponse'];
export type InvitationCreate = components['schemas']['InvitationCreate'];
export type InvitationPage = components['schemas']['InvitationListResponse'];
export type InvitationTokenRequest = components['schemas']['InvitationPreviewRequest'];
export type InvitationPreview = components['schemas']['InvitationPreviewResponse'];
export type InvitationAcceptance = components['schemas']['InvitationAcceptanceResponse'];
export type InvitationStatus = Invitation['status'];

export const invitationQueryKeys = {
  all: ['invitations'] as const,
  project: (projectId: string) => [...invitationQueryKeys.all, projectId] as const,
  list: (projectId: string, page: number) =>
    [...invitationQueryKeys.project(projectId), 'list', page] as const,
};
