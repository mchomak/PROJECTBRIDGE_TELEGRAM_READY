# Stage 08 — Document Management and Lifecycle

**Goal:** Allow both project participants to upload and access shared
documents and manage their lifecycle with mutual consent.

## Read first

- `AGENTS.md`
- `docs/product/MVP_SCOPE.md`
- `docs/database/DATA_MODEL.md` — Documents and lifecycle
- `docs/api/API_CONTRACT.md` — Documents
- `docs/documents/DOCUMENT_LIFECYCLE.md`
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`
- `docs/OPEN_DECISIONS.md` items 27–28

## Dependencies

Stages 02 and 03. Project State may be developed in parallel if API
ownership is clear.

## Required documentation alignment before coding

The earlier product decision was: a document is first moved to an
archive, becomes hidden from the active list, remains restorable, and
only then may proceed toward permanent deletion with both participants’
consent.

The current lifecycle/API documents do not clearly enforce that
archive-first sequence. Resolve and update the state machine, database
model, and API contract before implementation.

Also confirm whether the documented 30-day cancellation window is
approved. Do not hard-code an unconfirmed grace period.

## Scope

### Backend

- Implement Document, DocumentLifecycleRequest, and
  DocumentLifecycleApproval.
- Support shared documents only. Do not add a visibility/private field.
- Allow either project participant to upload and download documents.
- Enforce the 20 MB limit on the server.
- Support only PDF, DOCX, TXT, and Markdown text-bearing files.
- Validate file extension and detected MIME type.
- Generate internal storage keys; never use original filenames as
  filesystem paths.
- Store bytes outside PostgreSQL using a storage abstraction and
  persistent local volume.
- Authorize every download.
- Implement the approved archive, restore, and mutual-consent
  permanent-deletion state machine.
- Record both participants’ decisions and audit lifecycle actions.
- Exclude archived and deletion-pending documents from active lists and
  future retrieval.

### Frontend

- Shared project document list.
- Upload control with size/type validation feedback.
- Document details and processing/lifecycle status.
- Download action.
- Archive request, approval/rejection, restore, and deletion request UI.
- Make pending consent and irreversible consequences explicit.

## Out of scope

- Private documents.
- OCR or image understanding.
- Audio/video processing.
- Public URL import.
- Full-text extraction and embeddings; those are Stage 09.
- Production malware scanning unless already available in the
  environment. Record it as a production gate.

## Deliverables

- Document metadata and lifecycle models.
- Local persistent file storage.
- Upload/download endpoints and UI.
- Mutual-consent lifecycle workflow.
- File validation and security tests.

## Acceptance criteria

- [ ] Both participants can list, upload, and download all project
  documents.
- [ ] No private-document visibility concept exists.
- [ ] Files larger than 20 MB are rejected server-side.
- [ ] Unsupported formats are rejected server-side.
- [ ] Original filenames cannot cause path traversal or overwrite
  another file.
- [ ] Downloads require active project membership.
- [ ] Archive requires approval from both participants.
- [ ] An archived document is absent from the active list and can be
  restored.
- [ ] Permanent deletion requires both participants’ explicit consent.
- [ ] Permanent deletion follows the approved archive-first sequence.
- [ ] Lifecycle actions are audited.
- [ ] Tests cover upload limits, invalid MIME types, unauthorized
  downloads, consent, rejection, restoration, and deletion eligibility.

## Stop conditions

Do not implement permanent deletion until the archive-first discrepancy
and grace-period decision are resolved. Do not invent a file retention
period or claim backups are immediately purged.

## Codex handoff

Implement Stage 08 only after the lifecycle documents have been
reconciled. Follow the approved state machine exactly; all project
documents are shared.
