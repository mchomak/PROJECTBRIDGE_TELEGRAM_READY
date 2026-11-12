import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  decideProjectDocumentLifecycle,
  documentQueryKeys,
  requestProjectDocumentLifecycle,
  restoreProjectDocument,
  uploadProjectDocument,
  type ProjectDocument,
  type ProjectDocumentLifecycleAction,
  type ProjectDocumentLifecycleRequest,
} from '../../../entities/documents';

export type DocumentLifecycleActionVariables =
  | {
      type: 'request';
      documentId: string;
      action: ProjectDocumentLifecycleAction;
    }
  | {
      type: 'approve' | 'reject' | 'cancel';
      documentId: string;
      requestId: string;
    }
  | {
      type: 'restore';
      documentId: string;
    };

export type DocumentLifecycleResult = ProjectDocument | ProjectDocumentLifecycleRequest;

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

function executeDocumentLifecycleAction(
  action: DocumentLifecycleActionVariables,
): Promise<DocumentLifecycleResult> {
  if (action.type === 'request') {
    return requestProjectDocumentLifecycle(action.documentId, action.action);
  }
  if (action.type === 'restore') {
    return restoreProjectDocument(action.documentId);
  }
  return decideProjectDocumentLifecycle(action.requestId, action.type);
}

export function useDocumentLifecycleAction(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation<DocumentLifecycleResult, Error, DocumentLifecycleActionVariables>({
    mutationFn: executeDocumentLifecycleAction,
    onSettled: async () => {
      await queryClient.invalidateQueries({
        queryKey: documentQueryKeys.project(projectId),
      });
    },
  });
}
