import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  downloadProjectDocument,
  useProjectDocuments,
  type ProjectDocument,
  type ProjectDocumentListStatus,
} from '../../../entities/documents';
import {
  useDocumentLifecycleAction,
  useUploadProjectDocument,
  type DocumentLifecycleActionVariables,
} from '../../../features/documents';
import './ProjectDocumentsPanel.css';

const MAX_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024;
const SUPPORTED_EXTENSIONS = new Set(['pdf', 'docx', 'txt', 'md', 'markdown']);

function validateFile(file: File): string | null {
  const extension = file.name.split('.').at(-1)?.toLowerCase();
  if (!extension || !SUPPORTED_EXTENSIONS.has(extension)) {
    return 'Choose a PDF, DOCX, TXT, or Markdown file.';
  }
  if (file.size > MAX_DOCUMENT_SIZE_BYTES) {
    return 'Files must be 20 MiB or smaller.';
  }
  return null;
}

function formatFileSize(size: number): string {
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MiB`;
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KiB`;
  return `${size} bytes`;
}

function processingLabel(status: ProjectDocument['processing_status']): string {
  if (status === 'queued') return 'Queued';
  if (status === 'processing') return 'Processing';
  if (status === 'ready') return 'Ready';
  if (status === 'failed') return 'Processing failed';
  return 'Unsupported';
}

function remainingTime(deadline: string, now: number): string {
  const remainingMinutes = Math.ceil((new Date(deadline).getTime() - now) / 60_000);
  if (remainingMinutes <= 0) return 'The cancellation window has ended. Deletion is queued.';

  const days = Math.floor(remainingMinutes / (24 * 60));
  const hours = Math.floor((remainingMinutes % (24 * 60)) / 60);
  const minutes = remainingMinutes % 60;
  return `${days}d ${hours}h ${minutes}m until permanent deletion.`;
}

function retryLabel(label: string, failed: boolean): string {
  if (!failed) return label;
  if (label === 'Request archive') return 'Retry archive request';
  if (label === 'Request permanent deletion') return 'Retry deletion request';
  return `Retry ${label.toLowerCase()}`;
}

export function ProjectDocumentsPanel({
  projectId,
  canUpload,
  canManageLifecycle,
  currentUserId,
}: {
  projectId: string;
  canUpload: boolean;
  canManageLifecycle: boolean;
  currentUserId: string;
}) {
  const [page, setPage] = useState(1);
  const [listStatus, setListStatus] = useState<ProjectDocumentListStatus>('active');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [lifecycleMessage, setLifecycleMessage] = useState<string | null>(null);
  const [clock, setClock] = useState(Date.now());
  const fileInput = useRef<HTMLInputElement>(null);
  const documents = useProjectDocuments(projectId, page, listStatus);
  const upload = useUploadProjectDocument(projectId);
  const lifecycle = useDocumentLifecycleAction(projectId);

  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  function runLifecycleAction(variables: DocumentLifecycleActionVariables, label: string) {
    setLifecycleMessage(null);
    setPage(1);
    lifecycle.mutate(variables, {
      onSuccess: () => setLifecycleMessage(`${label} updated.`),
    });
  }

  function isFailedAction(variables: DocumentLifecycleActionVariables): boolean {
    const failed = lifecycle.variables;
    if (!lifecycle.isError || !failed || failed.type !== variables.type) return false;
    if (failed.documentId !== variables.documentId) return false;
    if (failed.type === 'request' && variables.type === 'request') {
      return failed.action === variables.action;
    }
    if (failed.type === 'request' || variables.type === 'request') return false;
    if (failed.type === 'restore' || variables.type === 'restore') {
      return failed.type === variables.type;
    }
    return failed.type === variables.type && failed.requestId === variables.requestId;
  }

  function chooseFile(file: File | null) {
    upload.reset();
    setSelectedFile(file);
    setValidationError(file ? validateFile(file) : null);
    setUploadSuccess(null);
    setUploadProgress(0);
  }

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile || validateFile(selectedFile)) return;

    setUploadProgress(0);
    setUploadSuccess(null);
    upload.mutate(
      { file: selectedFile, onProgress: setUploadProgress },
      {
        onSuccess: (document) => {
          setUploadSuccess(`${document.original_filename} uploaded. Processing is queued.`);
          setSelectedFile(null);
          setValidationError(null);
          setPage(1);
          if (fileInput.current) fileInput.current.value = '';
        },
      },
    );
  }

  async function download(document: ProjectDocument) {
    setDownloadingId(document.id);
    setDownloadError(null);
    try {
      await downloadProjectDocument(document.id, document.original_filename);
    } catch (error) {
      setDownloadError(
        error instanceof Error ? error.message : 'The document could not be downloaded.',
      );
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <section className="project-panel documents-panel" aria-labelledby="documents-title">
      <div className="section-heading">
        <div>
          <h2 id="documents-title">Shared documents</h2>
          <p className="section-heading__description">
            Both project participants can upload and download these files.
          </p>
        </div>
        <span className="section-heading__note">20 MiB max</span>
      </div>

      {canUpload ? (
        <form className="document-upload" onSubmit={submitUpload} noValidate>
          <div className="form-field">
            <label htmlFor="project-document-file">Choose a document</label>
            <input
              accept=".pdf,.docx,.txt,.md,.markdown"
              aria-describedby={validationError ? 'document-upload-error' : undefined}
              aria-invalid={Boolean(validationError)}
              id="project-document-file"
              onChange={(event) => chooseFile(event.currentTarget.files?.[0] ?? null)}
              ref={fileInput}
              type="file"
            />
            {selectedFile && !validationError && (
              <p className="document-upload__selection">
                {selectedFile.name} · {formatFileSize(selectedFile.size)}
              </p>
            )}
            {validationError && (
              <p className="field-error" id="document-upload-error" role="alert">
                {validationError}
              </p>
            )}
          </div>
          <div className="document-upload__actions">
            <button
              className="button button--primary"
              disabled={!selectedFile || Boolean(validationError) || upload.isPending}
              type="submit"
            >
              {upload.isPending
                ? 'Uploading…'
                : upload.isError
                  ? 'Retry upload'
                  : 'Upload document'}
            </button>
          </div>
          {upload.isPending && (
            <div className="document-upload__progress">
              <progress aria-label="Document upload progress" max={100} value={uploadProgress} />
              <span role="status">{uploadProgress}% uploaded</span>
            </div>
          )}
          {upload.isError && (
            <p className="form-error" role="alert">
              {upload.error.message || 'The upload failed. Your selected file is ready to retry.'}
            </p>
          )}
          {uploadSuccess && (
            <p className="success-message" role="status">
              {uploadSuccess}
            </p>
          )}
        </form>
      ) : (
        <p className="document-upload__readonly">
          Uploading is available while the project is a draft or active.
        </p>
      )}

      <fieldset className="document-views">
        <legend>Document views</legend>
        {(
          [
            ['active', 'Active'],
            ['archived', 'Archive'],
            ['deletion_pending', 'Deletion pending'],
          ] as const
        ).map(([status, label]) => (
          <button
            aria-pressed={listStatus === status}
            className="button button--secondary"
            key={status}
            onClick={() => {
              setListStatus(status);
              setPage(1);
            }}
            type="button"
          >
            {label}
          </button>
        ))}
      </fieldset>

      {!canManageLifecycle && (
        <p className="document-upload__readonly">
          New lifecycle actions, decisions, and restoration are available while the project is a
          draft or active.
        </p>
      )}

      {downloadError && (
        <p className="form-error" role="alert">
          {downloadError}
        </p>
      )}
      {lifecycle.error && (
        <p className="form-error" role="alert">
          {lifecycle.error.message || 'The document lifecycle action could not be completed.'}
        </p>
      )}
      {lifecycleMessage && (
        <p className="success-message" role="status">
          {lifecycleMessage}
        </p>
      )}

      {documents.isPending ? (
        <p className="state-message" role="status">
          Loading shared documents…
        </p>
      ) : documents.isError ? (
        <section className="state-message state-message--error" aria-labelledby="documents-error">
          <h3 id="documents-error">We couldn’t load the documents</h3>
          <p>{documents.error.message || 'Check your connection and try again.'}</p>
          <button
            className="button button--secondary"
            onClick={() => void documents.refetch()}
            type="button"
          >
            Try again
          </button>
        </section>
      ) : documents.data.results.length === 0 ? (
        <p className="document-empty-state">No shared documents yet.</p>
      ) : (
        <>
          <p className="document-count">
            {documents.data.count} {documents.data.count === 1 ? 'document' : 'documents'}
          </p>
          <ul className="document-list">
            {documents.data.results.map((document) => {
              const lifecycleRequest = document.lifecycle_request;
              return (
                <li className="document-row" key={document.id}>
                  <div className="document-row__main">
                    <h3>{document.original_filename}</h3>
                    <p>
                      {document.mime_type} · {formatFileSize(document.file_size)}
                    </p>
                  </div>
                  <div className="document-row__status">
                    <span className="status-badge">
                      {processingLabel(document.processing_status)}
                    </span>
                    <span>{new Date(document.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="document-row__actions">
                    <button
                      className="button button--secondary"
                      disabled={downloadingId === document.id}
                      onClick={() => void download(document)}
                      type="button"
                    >
                      {downloadingId === document.id ? 'Downloading…' : 'Download'}
                    </button>
                    {document.lifecycle_status === 'active' && canManageLifecycle && (
                      <button
                        className="button button--secondary"
                        disabled={lifecycle.isPending}
                        onClick={() =>
                          runLifecycleAction(
                            {
                              type: 'request',
                              documentId: document.id,
                              action: 'archive',
                            },
                            'Archive request',
                          )
                        }
                        type="button"
                      >
                        {retryLabel(
                          'Request archive',
                          isFailedAction({
                            type: 'request',
                            documentId: document.id,
                            action: 'archive',
                          }),
                        )}
                      </button>
                    )}
                    {document.lifecycle_status === 'archive_pending' && (
                      <div className="document-lifecycle-status">
                        <p role="status">
                          Archive consent: {lifecycleRequest?.approvals.length ?? 1} of 2
                          participants.
                        </p>
                        {canManageLifecycle &&
                          lifecycleRequest &&
                          lifecycleRequest.initiated_by_id !== currentUserId &&
                          lifecycleRequest.viewer_decision === null && (
                            <>
                              <button
                                className="button button--primary"
                                disabled={lifecycle.isPending}
                                onClick={() =>
                                  runLifecycleAction(
                                    {
                                      type: 'approve',
                                      documentId: document.id,
                                      requestId: lifecycleRequest.id,
                                    },
                                    'Archive decision',
                                  )
                                }
                                type="button"
                              >
                                {retryLabel(
                                  'Approve archive',
                                  isFailedAction({
                                    type: 'approve',
                                    documentId: document.id,
                                    requestId: lifecycleRequest.id,
                                  }),
                                )}
                              </button>
                              <button
                                className="button button--secondary"
                                disabled={lifecycle.isPending}
                                onClick={() =>
                                  runLifecycleAction(
                                    {
                                      type: 'reject',
                                      documentId: document.id,
                                      requestId: lifecycleRequest.id,
                                    },
                                    'Archive decision',
                                  )
                                }
                                type="button"
                              >
                                {retryLabel(
                                  'Reject archive',
                                  isFailedAction({
                                    type: 'reject',
                                    documentId: document.id,
                                    requestId: lifecycleRequest.id,
                                  }),
                                )}
                              </button>
                            </>
                          )}
                      </div>
                    )}
                    {document.lifecycle_status === 'archived' && (
                      <div className="document-lifecycle-status">
                        {lifecycleRequest?.status === 'pending' ? (
                          <>
                            <p role="status">
                              Deletion consent: {lifecycleRequest.approvals.length} of 2
                              participants.
                            </p>
                            {canManageLifecycle &&
                              lifecycleRequest.initiated_by_id !== currentUserId &&
                              lifecycleRequest.viewer_decision === null && (
                                <>
                                  <button
                                    className="button button--primary"
                                    disabled={lifecycle.isPending}
                                    onClick={() =>
                                      runLifecycleAction(
                                        {
                                          type: 'approve',
                                          documentId: document.id,
                                          requestId: lifecycleRequest.id,
                                        },
                                        'Deletion decision',
                                      )
                                    }
                                    type="button"
                                  >
                                    {retryLabel(
                                      'Approve deletion',
                                      isFailedAction({
                                        type: 'approve',
                                        documentId: document.id,
                                        requestId: lifecycleRequest.id,
                                      }),
                                    )}
                                  </button>
                                  <button
                                    className="button button--secondary"
                                    disabled={lifecycle.isPending}
                                    onClick={() =>
                                      runLifecycleAction(
                                        {
                                          type: 'reject',
                                          documentId: document.id,
                                          requestId: lifecycleRequest.id,
                                        },
                                        'Deletion decision',
                                      )
                                    }
                                    type="button"
                                  >
                                    {retryLabel(
                                      'Reject deletion',
                                      isFailedAction({
                                        type: 'reject',
                                        documentId: document.id,
                                        requestId: lifecycleRequest.id,
                                      }),
                                    )}
                                  </button>
                                </>
                              )}
                          </>
                        ) : (
                          <>
                            {canManageLifecycle && (
                              <>
                                <button
                                  className="button button--secondary"
                                  disabled={lifecycle.isPending}
                                  onClick={() =>
                                    runLifecycleAction(
                                      { type: 'restore', documentId: document.id },
                                      'Restore',
                                    )
                                  }
                                  type="button"
                                >
                                  {retryLabel(
                                    'Restore document',
                                    isFailedAction({ type: 'restore', documentId: document.id }),
                                  )}
                                </button>
                                <button
                                  className="button button--secondary"
                                  disabled={lifecycle.isPending}
                                  onClick={() =>
                                    runLifecycleAction(
                                      {
                                        type: 'request',
                                        documentId: document.id,
                                        action: 'permanent_delete',
                                      },
                                      'Deletion request',
                                    )
                                  }
                                  type="button"
                                >
                                  {retryLabel(
                                    'Request permanent deletion',
                                    isFailedAction({
                                      type: 'request',
                                      documentId: document.id,
                                      action: 'permanent_delete',
                                    }),
                                  )}
                                </button>
                              </>
                            )}
                            <p>
                              Permanent deletion requires both participants and has a 30-day
                              cancellation window after the second approval.
                            </p>
                            <p>
                              Encrypted backups may retain a copy until the applicable backup
                              expires.
                            </p>
                          </>
                        )}
                      </div>
                    )}
                    {document.lifecycle_status === 'deletion_pending' && (
                      <div className="document-lifecycle-status">
                        {lifecycleRequest?.deletion_after ? (
                          <>
                            <p role="status">
                              {remainingTime(lifecycleRequest.deletion_after, clock)}
                            </p>
                            <p>
                              Encrypted backups may retain a copy until the applicable backup
                              expires.
                            </p>
                            <button
                              className="button button--secondary"
                              disabled={
                                lifecycle.isPending ||
                                new Date(lifecycleRequest.deletion_after).getTime() <= clock
                              }
                              onClick={() =>
                                runLifecycleAction(
                                  {
                                    type: 'cancel',
                                    documentId: document.id,
                                    requestId: lifecycleRequest.id,
                                  },
                                  'Deletion cancellation',
                                )
                              }
                              type="button"
                            >
                              {retryLabel(
                                'Cancel permanent deletion',
                                isFailedAction({
                                  type: 'cancel',
                                  documentId: document.id,
                                  requestId: lifecycleRequest.id,
                                }),
                              )}
                            </button>
                          </>
                        ) : (
                          <p role="status">Deletion is scheduled after both approvals.</p>
                        )}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          {(documents.data.previous || documents.data.next) && (
            <nav className="document-pagination" aria-label="Document pages">
              <button
                className="button button--secondary"
                disabled={!documents.data.previous || documents.isFetching}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                type="button"
              >
                Previous documents
              </button>
              <span>Page {page}</span>
              <button
                className="button button--secondary"
                disabled={!documents.data.next || documents.isFetching}
                onClick={() => setPage((current) => current + 1)}
                type="button"
              >
                Next documents
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}
