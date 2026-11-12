import { apiJson, apiRequest, ApiError, type ApiErrorPayload } from '../../../shared/api';
import type { components } from '../../../shared/api/generated/schema';

export type ProjectDocument = components['schemas']['DocumentResponse'];
export type ProjectDocumentPage = components['schemas']['DocumentListResponse'];

type CsrfToken = components['schemas']['CsrfToken'];

function projectDocumentsPath(projectId: string): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/documents/`;
}

function documentPath(documentId: string): string {
  return `/api/v1/documents/${encodeURIComponent(documentId)}/`;
}

export function getProjectDocuments(
  projectId: string,
  page = 1,
  pageSize = 100,
): Promise<ProjectDocumentPage> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  return apiJson<ProjectDocumentPage>(`${projectDocumentsPath(projectId)}?${params.toString()}`);
}

export function uploadProjectDocument(
  projectId: string,
  file: File,
  onProgress: (progress: number) => void,
): Promise<ProjectDocument> {
  return apiJson<CsrfToken>('/api/v1/auth/csrf/').then(
    ({ csrf_token: csrfToken }) =>
      new Promise<ProjectDocument>((resolve, reject) => {
        const request = new XMLHttpRequest();
        request.open('POST', projectDocumentsPath(projectId));
        request.withCredentials = true;
        request.setRequestHeader('X-CSRFToken', csrfToken);
        request.upload.onprogress = (event) => {
          if (event.lengthComputable && event.total > 0) {
            onProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)));
          }
        };
        request.onload = () => {
          let payload: ProjectDocument | ApiErrorPayload | null = null;
          try {
            payload = JSON.parse(request.responseText) as ProjectDocument | ApiErrorPayload;
          } catch {
            payload = null;
          }

          if (request.status >= 200 && request.status < 300) {
            resolve(payload as ProjectDocument);
          } else {
            reject(new ApiError(request.status, payload as ApiErrorPayload | null));
          }
        };
        request.onerror = () =>
          reject(new Error('The upload failed. Check your connection and try again.'));
        request.onabort = () => reject(new Error('The upload was interrupted. Try again.'));
        request.send(
          (() => {
            const formData = new FormData();
            formData.append('file', file);
            return formData;
          })(),
        );
      }),
  );
}

export async function downloadProjectDocument(documentId: string, filename: string): Promise<void> {
  const response = await apiRequest(`${documentPath(documentId)}download/`);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
    throw new ApiError(response.status, payload);
  }

  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
