import { useRef, useState, type FormEvent } from 'react';
import {
  downloadProjectDocument,
  useProjectDocuments,
  type ProjectDocument,
} from '../../../entities/documents';
import { useUploadProjectDocument } from '../../../features/documents';
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

export function ProjectDocumentsPanel({
  projectId,
  canUpload,
}: {
  projectId: string;
  canUpload: boolean;
}) {
  const [page, setPage] = useState(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const documents = useProjectDocuments(projectId, page);
  const upload = useUploadProjectDocument(projectId);

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

      {downloadError && (
        <p className="form-error" role="alert">
          {downloadError}
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
            {documents.data.results.map((document) => (
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
                <button
                  className="button button--secondary"
                  disabled={downloadingId === document.id}
                  onClick={() => void download(document)}
                  type="button"
                >
                  {downloadingId === document.id ? 'Downloading…' : 'Download'}
                </button>
              </li>
            ))}
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
