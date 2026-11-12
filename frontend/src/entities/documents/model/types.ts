export const documentQueryKeys = {
  all: ['documents'] as const,
  project: (projectId: string) => [...documentQueryKeys.all, projectId] as const,
  page: (projectId: string, page: number, status: string = 'active') =>
    [...documentQueryKeys.project(projectId), status, page] as const,
};
