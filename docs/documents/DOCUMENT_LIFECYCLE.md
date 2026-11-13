# Document Storage and Lifecycle

**Status:** Shared visibility and mutual-consent lifecycle agreed  
**Last updated:** 2026-11-13

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
2.  Extract text using pypdf for PDF, python-docx for DOCX, and strict
    UTF-8/UTF-16/UTF-32 decoding for TXT and Markdown. OCR is not used.
3.  Split extracted text into chunks of at most 1000 Unicode characters
    with 150 characters of overlap. Chunks do not cross PDF pages or
    DOCX paragraphs/table cells; source offsets are stored as metadata.
4.  Store DocumentChunk records.
5.  Generate embeddings through the AI Router's `document_embedding`
    task using `text-embedding-3-small` (1536 dimensions).
6.  Store vectors in pgvector with cosine HNSW indexing.
7.  Mark the document ready or failed/unsupported.

The upload request must not wait for extraction, embedding, or AI
analysis to finish. The Celery task is queued only after the upload
transaction commits and has a 180-second soft and 240-second hard time
limit. Before `ZipFile` builds its member list, DOCX ZIP64 archives,
archives with more than 10,000 entries, or central directories over 2
MiB are rejected. DOCX content is limited to 50 MiB uncompressed, PDF
files to 5000 pages, and extracted text to 2 million characters. These
limits are processing safeguards, not changes to the 20 MiB upload
limit.

The frontend reads document processing status through the document API.

The upload transaction commits document metadata and the storage key before
the Celery task is published. A broker failure after commit leaves the
database row and uploaded file intact. A Beat sweep runs every 60 seconds and
recovers queued documents older than one minute using a row-locked two-minute
dispatch lease. A publish exception is ambiguous because the broker can accept
the message before the publisher sees a connection error. Retry frequency uses
exponential backoff from 30 seconds to 30 minutes with a stored exception-count
cap of 12; after five exceptions the
document API exposes `processing_dispatch_error_code=queue_unavailable` while
`processing_status` remains `queued`. Beat continues recovery automatically
without manual database edits. After five dispatch reservations without a
worker claim, the API exposes `processing_dispatch_error_code=worker_backlog`;
it is also nonterminal and clears on worker claim. In both cases, user-facing
copy says processing is waiting and retries continue without asserting that an
ambiguous publish was accepted. The same generation-scoped task ID stays valid
until a worker claims it. Dispatch attempts never advance the processing
generation; only a worker claim does. Each processing attempt has a six-minute
lease, longer than its four-minute hard task limit. The sweep also requeues
expired or legacy processing rows with no lease. It only processes active or
archived documents, so lifecycle rules continue to govern RAG eligibility.
Stable generation-scoped task IDs and generation fencing prevent stale or
duplicate workers from replacing newer chunks or embeddings.

## 5. RAG eligibility

Only active, successfully processed documents are eligible for
retrieval. `archive_pending` is excluded immediately while the second
participant decides.

Archived and deletion-pending documents are also excluded from retrieval
immediately.

When a document is restored, its existing chunks and embeddings may be
re-enabled if they remain valid and have not been purged.

A scanned/image-only PDF with no text layer is marked `unsupported`;
malformed files or processing/provider errors are marked `failed`. A
missing embedding configuration leaves extracted chunks stored but does
not create vectors or mark the document ready. A document whose
processing failed remains visible to participants with its failure
status; it must not be silently treated as searchable.

Retrieval embeds the query using the same active profile/version/model
tuple as the stored vectors, uses cosine distance, and returns the five
nearest chunks by default without a score cutoff or reranking. Only the current
project's active member and documents in `active` lifecycle state with
`ready` processing status are eligible. Evidence identifies the document
and chunk and carries its filename, page/paragraph/character location,
and source text.

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

1.  Either active project participant may request archive for an
    `active` document while the project is `draft` or `active`; both
    active roles must exist.
2.  The request records the initiator’s approval and changes the
    document to `archive_pending`. The document remains in the active
    list but is excluded from RAG while the other participant decides.
3.  The other active participant may approve or reject.
4.  Approval changes the request to `approved` and the document to
    `archived`. The document leaves the active list; source and derived
    data remain recoverable.
5.  Rejection changes the request to `rejected` and returns the document
    to `active`.
6.  Either active project member may restore an `archived` document to
    `active` as a separate action while the parent project is `draft` or
    `active`. Restoration is audited. Restoration is not part of archive
    approval. If a permanent-delete request is still `pending` with only
    the initiator's approval, restoration cancels that request in the
    same transaction and records both lifecycle actions. A deletion that
    has already received both approvals must first be explicitly
    cancelled while its deadline is open; only then can the archived
    document be restored.

All request creation, approve/reject decisions, and restore actions
require active project membership and a mutable parent project
(`draft`/`active`). Cross-project or inactive-member IDs return `404`.

## 8. Permanent deletion workflow

1.  Either active project participant may request permanent deletion
    only for an `archived` document while the parent project is `draft`
    or `active`; both active roles must exist.
2.  The request records the initiator’s approval. The document remains
    `archived` until the other participant decides.
3.  The other active participant may approve or reject. Rejection leaves
    the document `archived` and marks the request `rejected`.
4.  The second approval changes the document to `deletion_pending` and
    sets the cancellation deadline to exactly 30 days after that
    approval. `deletion_after` remains null before the second approval.
5.  Either active project member may cancel only while the current time
    is strictly earlier than the deadline. At the deadline cancellation
    is no longer available. Cancellation marks the request `cancelled`
    and returns the document to `archived`; restoration remains a
    separate action.
6.  Cancellation remains available before the deadline even if the
    project has since completed or been archived. It withdraws prior
    consent.
7.  Celery Beat checks due requests every five minutes. After the
    deadline, the sweep completes an approved deletion even if the
    parent project has since completed or been archived. Cancelled and
    stale requests are no-ops. The task is retry-safe.

The deletion process must remove:

- original file;
- extracted text;
- document chunks;
- embeddings;
- generated previews or derivatives;
- application caches that contain document content.

The Stage 08 document row is retained as a tombstone with lifecycle
status `deleted`, `deleted_at`, empty original filename/MIME type, zero
size, and the empty-content SHA-256 digest. Its private storage key is
retained only to preserve uniqueness and is never returned. Lifecycle
request/approval rows remain as the consent record; one minimal
content-free `ProjectAuditLog` event records the mutually approved
deletion. Stage 09 must extend cleanup to chunks and embeddings before
extraction is enabled.

Do not retain deleted content in lifecycle audit metadata, operational
logs, or other application storage.

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
