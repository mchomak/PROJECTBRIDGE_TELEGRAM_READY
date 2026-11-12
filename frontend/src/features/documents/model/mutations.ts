import { useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadProjectDocument, type ProjectDocument } from '../../../entities/documents';
import { documentQueryKeys } from '../../../entities/documents';

export type UploadDocumentVariables = {
  file: File;
  onProgress: (progress: number) => void;
};

export function useUploadProjectDocument(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<ProjectDocument, Error, UploadDocumentVariables>({
    mutationFn: ({ file, onProgress }) => uploadProjectDocument(projectId, file, onProgress),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: documentQueryKeys.project(projectId),
      });
    },
  });
}
