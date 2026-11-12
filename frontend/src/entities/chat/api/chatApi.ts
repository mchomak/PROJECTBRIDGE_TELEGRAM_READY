import { apiJson } from '../../../shared/api';
import type { components } from '../../../shared/api/generated/schema';

export type ChatMessage = components['schemas']['MessageResponse'];
export type ChatMessagePage = components['schemas']['MessagePageResponse'];
export type ChatMessageCreate = components['schemas']['MessageCreate'];

function projectPath(projectId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/messages/`;
}

export function getProjectMessages(
  projectId: string,
  cursor?: string,
  pageSize = 50,
): Promise<ChatMessagePage> {
  const params = new URLSearchParams({ page_size: String(pageSize) });
  if (cursor) params.set('cursor', cursor);
  return apiJson<ChatMessagePage>(`${projectPath(projectId)}?${params.toString()}`);
}

export function createProjectMessage(
  projectId: string,
  data: ChatMessageCreate,
): Promise<ChatMessage> {
  return apiJson<ChatMessage>(projectPath(projectId), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export function getProjectMessageCursor(next: string | null): string | undefined {
  if (!next) return undefined;
  try {
    return new URL(next).searchParams.get('cursor') ?? undefined;
  } catch {
    return undefined;
  }
}
