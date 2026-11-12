export const documentQueryKeys = {
  all: ['documents'] as const,
  project: (projectId: string) => [...documentQueryKeys.all, projectId] as const,
  page: (projectId: string, page: number) =>
    [...documentQueryKeys.project(projectId), page] as const,
};
