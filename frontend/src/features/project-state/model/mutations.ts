import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createProjectStateRecord,
  updateProjectStateRecord,
} from '../../../entities/project-state';
import { projectStateQueryKeys } from '../../../entities/project-state';
import type {
  ProjectStateCollection,
  ProjectStateCreateByCollection,
  ProjectStateRecordKind,
  ProjectStateResponseByCollection,
  ProjectStateResponseByKind,
  ProjectStatePatchByKind,
} from '../../../entities/project-state';

export function useCreateProjectStateRecord<K extends ProjectStateCollection>(
  projectId: string,
  collection: K,
) {
  const queryClient = useQueryClient();
  return useMutation<ProjectStateResponseByCollection[K], Error, ProjectStateCreateByCollection[K]>(
    {
      mutationFn: (data) => createProjectStateRecord(projectId, collection, data),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: projectStateQueryKeys.project(projectId) });
      },
    },
  );
}

export function useUpdateProjectStateRecord<K extends ProjectStateRecordKind>(
  projectId: string,
  kind: K,
) {
  const queryClient = useQueryClient();
  return useMutation<
    ProjectStateResponseByKind[K],
    Error,
    { recordId: string; changes: ProjectStatePatchByKind[K] }
  >({
    mutationFn: ({ recordId, changes }) => updateProjectStateRecord(kind, recordId, changes),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectStateQueryKeys.project(projectId) });
    },
  });
}
