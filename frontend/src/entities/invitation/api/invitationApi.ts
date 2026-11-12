import { apiJson } from '../../../shared/api';
import type { Invitation, InvitationCreate, InvitationPage } from '../model/types';

function invitationsPath(projectId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/invitations/`;
}

export function getProjectInvitations(projectId: string, page = 1): Promise<InvitationPage> {
  const params = new URLSearchParams({ page: String(page), page_size: '100' });
  return apiJson<InvitationPage>(`${invitationsPath(projectId)}?${params.toString()}`);
}

export function createProjectInvitation(
  projectId: string,
  data: InvitationCreate,
): Promise<Invitation> {
  return apiJson<Invitation>(invitationsPath(projectId), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export function revokeProjectInvitation(
  projectId: string,
  invitationId: string,
): Promise<Invitation> {
  return apiJson<Invitation>(
    `${invitationsPath(projectId)}${encodeURIComponent(invitationId)}/revoke/`,
    { method: 'POST' },
  );
}
