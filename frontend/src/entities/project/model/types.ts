import type { components } from '../../../shared/api/generated/schema';

export type Project = components['schemas']['ProjectResponse'];
export type ProjectType = components['schemas']['ProjectTypeEnum'];
export type ProjectStatus = components['schemas']['ProjectStatusEnum'];
export type ProjectMember = components['schemas']['ProjectMemberSummary'];
export type ProjectPage = components['schemas']['ProjectListResponse'];
export type ProjectPassport = components['schemas']['ProjectPassportResponse'];

export const projectTypeOptions: ReadonlyArray<{ value: ProjectType; label: string }> = [
  { value: 'website', label: 'Сайт' },
  { value: 'telegram_bot', label: 'Telegram-бот' },
  { value: 'automation', label: 'Автоматизация' },
  { value: 'other', label: 'Другое' },
];

export const projectStatusLabels: Record<ProjectStatus, string> = {
  draft: 'Черновик',
  active: 'Активен',
  completed: 'Завершён',
  archived: 'В архиве',
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
