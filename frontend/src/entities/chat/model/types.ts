export const chatQueryKeys = {
  all: ['chat'] as const,
  project: (projectId: string) => [...chatQueryKeys.all, projectId] as const,
  history: (projectId: string) => [...chatQueryKeys.project(projectId), 'history'] as const,
};
