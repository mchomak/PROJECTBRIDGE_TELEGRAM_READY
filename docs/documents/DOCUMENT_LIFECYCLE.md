# Document Storage and Lifecycle

**Status:** Shared visibility and mutual-consent lifecycle agreed  
**Last updated:** 2026-11-11

## 1. Scope

The MVP supports project documents uploaded by either the executor or
the customer.

All documents are shared with both project participants. Private
documents do not exist.

## 2. Supported files

| Format                     | MVP handling                                             |
|:---------------------------|:---------------------------------------------------------|
| PDF                        | Text extraction                                          |
| DOCX                       | Text extraction                                          |
| TXT                        | Read as text                                             |
| MD                         | Read as text                                             |
| Scanned PDF/image-only PDF | Unsupported unless it contains an extractable text layer |

Limits:

- Maximum file size: `20 * 1024 * 1024` bytes per file (20 MiB).
- No OCR.
- No audio transcription.
- No video processing.
- No image understanding.

The server enforces the size limit and requires a supported extension to
match detected content. It recognizes PDF signatures, DOCX ZIP
containers with `[Content_Types].xml` and `word/document.xml`, and valid
text content for TXT and Markdown. Browser-provided MIME types are not
trusted. Client-side validation is only a usability aid.
Zero-byte TXT and Markdown files are valid text documents and are stored
with `processing_status=queued`.

## 3. Storage

Store file bytes outside PostgreSQL.

Local development uses Django's default storage rooted at `/app/media`,
backed by the persistent Compose `media` volume. Production may use
S3-compatible object storage without changing document business logic.

The database stores metadata and a unique internal UUID-based
`storage_key`. Generate storage keys independently of the original
filename. Keep the storage key out of API responses and do not expose
file bytes through a public URL. Downloads stream through an authenticated
backend endpoint with `Content-Disposition: attachment` and
`X-Content-Type-Options: nosniff`.

The original filename is metadata for display only.

## 4. Processing pipeline

Document processing is asynchronous. Stage 08 validates and stores the
original file, creates metadata with `processing_status=queued`, and
returns without extraction. Stage 09 owns the processing worker and
subsequent transitions:

1.  Enqueue processing after the database transaction commits.
2.  Extract text using a format-specific parser.
3.  Split extracted text into chunks.
4.  Store DocumentChunk records.
5.  Generate embeddings using the active embedding profile.
6.  Store vectors in pgvector.
7.  Mark the document ready or failed/unsupported.

The upload request must not wait for extraction, embedding, or AI
analysis to finish.

The frontend reads document processing status through the document API.

## 5. RAG eligibility

Only active, successfully processed documents are eligible for
retrieval.

Archived documents and documents pending permanent deletion must be
excluded from retrieval immediately.

When a document is restored, its existing chunks and embeddings may be
re-enabled if they remain valid and have not been purged.

A document whose processing failed remains visible to participants with
its failure status; it must not be silently treated as searchable.

## 6. Lifecycle states

Document lifecycle states:

- `active`
- `archive_pending`
- `archived`
- `deletion_pending`
- `deleted`

Processing states are separate:

- `queued`
- `processing`
- `ready`
- `failed`
- `unsupported`

## 7. Archive workflow

1.  Either participant requests archive.
2.  The request records the initiator’s approval.
3.  The other participant is asked to approve or reject.
4.  If both approve, the document becomes archived.
5.  The document disappears from the active document list and is
    excluded from RAG.
6.  The original file and derived data remain recoverable.
7.  Either participant may restore the archived document. Restoration is
    audited.

A rejected request does not archive the document.

## 8. Permanent deletion workflow

1.  Either participant requests permanent deletion.
2.  The request records the initiator’s approval.
3.  The other participant must approve.
4.  If both approve, the document enters `deletion_pending`.
5.  A 30-day cancellation period begins.
6.  Either participant may cancel during this period.
7.  If not cancelled, a background task permanently deletes the source
    file and derived data.

The deletion process must remove:

- original file;
- extracted text;
- document chunks;
- embeddings;
- generated previews or derivatives;
- application caches that contain document content.

Keep only a minimal audit record that the document was deleted by mutual
consent. Do not retain the deleted content in the audit log.

## 9. Backup behavior

Encrypted backups retain deleted files until the applicable operational
backup expires. A 14-day rolling period was previously proposed but is
not approved; do not present it as a product promise or implement a fixed
expiry from that proposal.

The system must not claim that a document is immediately erased from
every backup copy. A fixed backup expiry window can be communicated only
after an operational retention schedule is approved.

## 10. Required safeguards

- Validate size, extension, and detected content type.
- Generate safe internal storage keys.
- Prevent path traversal.
- Keep files outside public web roots.
- Authorize every download.
- Limit parser CPU, memory, and execution time.
- Handle malformed files safely.
- Treat extracted text as untrusted input when passed to AI.
- Malware scanning is not available in this MVP environment. Selecting
  and deploying a scanner is a production gate before public launch;
  uploaded files are not represented as scanned.
