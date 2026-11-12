import type { components } from '../../../shared/api/generated/schema';

export type Project = components['schemas']['ProjectResponse'];
export type ProjectType = components['schemas']['ProjectTypeEnum'];
export type ProjectStatus = components['schemas']['ProjectStatusEnum'];
export type ProjectMember = components['schemas']['ProjectMemberSummary'];
export type ProjectPage = components['schemas']['ProjectListResponse'];
export type ProjectPassport = components['schemas']['ProjectPassportResponse'];

export const projectTypeOptions: ReadonlyArray<{ value: ProjectType; label: string }> = [
  { value: 'website', label: 'Website' },
  { value: 'telegram_bot', label: 'Telegram bot' },
  { value: 'automation', label: 'Automation' },
  { value: 'other', label: 'Other' },
];

export const projectStatusLabels: Record<ProjectStatus, string> = {
  draft: 'Draft',
  active: 'Active',
  completed: 'Completed',
  archived: 'Archived',
};

export const projectQueryKeys = {
  all: ['projects'] as const,
  lists: () => [...projectQueryKeys.all, 'list'] as const,
  list: (status: 'archived' | 'ordinary', page: number) =>
    [...projectQueryKeys.lists(), status, page] as const,
  detail: (projectId: string) => [...projectQueryKeys.all, 'detail', projectId] as const,
  members: (projectId: string) => [...projectQueryKeys.all, 'members', projectId] as const,
  passport: (projectId: string) => [...projectQueryKeys.all, 'passport', projectId] as const,
};
