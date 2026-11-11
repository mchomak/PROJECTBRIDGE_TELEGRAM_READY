# ProjectBridge Database Model

**Status:** Logical model baseline; detailed field constraints must be
finalized before migrations  
**Database:** PostgreSQL  
**Last updated:** 2026-11-11

## 1. Database conventions

- Primary keys: UUID.
- Timestamps: timezone-aware UTC values.
- Django: `USE_TZ = True`.
- Monetary values: `DECIMAL`, never floating-point.
- Structured variable data: JSONB only where the structure is genuinely
  variable.
- Foreign keys: explicit relational constraints.
- Deletion: use explicit lifecycle rules; do not apply cascade deletion
  indiscriminately.
- Indexes: add indexes for foreign keys, project-scoped lists, status
  filters, and common sort orders.
- Vector search: pgvector. The embedding dimension and index strategy
  must be selected with the initial embedding model.

## 2. Accounts

### `User`

| Field               | Type / rule          | Notes                                    |
|:--------------------|:---------------------|:-----------------------------------------|
| `id`                | UUID, PK             | User identifier                          |
| `email`             | Unique email         | Login identifier; normalize consistently |
| `password`          | Django password hash | Never store plaintext                    |
| `first_name`        | String               | Required or optionality to be finalized  |
| `last_name`         | String               | Required or optionality to be finalized  |
| `email_verified_at` | Nullable timestamp   | Null until verified                      |
| `is_active`         | Boolean              | Django account activation                |
| `created_at`        | Timestamp            | Creation time                            |
| `updated_at`        | Timestamp            | Last update                              |

Use a custom Django user model based on `AbstractUser`, configured for
email-based authentication. Set it before the first migration.

### `EmailVerificationToken`

Fields: `id`, `user_id`, `token_hash`, `expires_at`, `used_at`,
`created_at`.

Store only a hash of the verification token. Enforce single use and
expiration.

## 3. Projects and membership

### `Project`

Fields:

- `id` — UUID, PK
- `name` — string
- `description` — text, nullable
- `project_type` — choice: `website`, `telegram_bot`, `automation`,
  `other`
- `status` — choice: `draft`, `active`, `completed`, `archived`
- `created_by_id` — FK to User
- `created_at`, `updated_at`
- `completed_at`, nullable
- `archived_at`, nullable

### `ProjectMember`

Fields: `id`, `project_id`, `user_id`, `role`, `status`, `joined_at`.

Roles: `executor`, `customer`.  
Membership status should distinguish active membership from revoked/left
membership.

Constraints:

- A user must not have duplicate membership rows for the same project.
- A project may have only one active executor and one active customer.
- Enforce the one-active-member-per-role rule at the database level,
  using a conditional unique constraint where supported.

### `ProjectPassport`

One-to-one with Project.

Proposed fields:

- `id`
- `project_id` — unique FK/OneToOne
- `goal` — text
- `target_audience` — text
- `expected_result` — text
- `functional_scope` — JSONB
- `integrations` — JSONB
- `constraints` — JSONB
- `deadline` — date, nullable
- `budget_min` — decimal, nullable
- `budget_max` — decimal, nullable
- `currency` — 3-character currency code, nullable
- `additional_data` — JSONB
- `version` — integer for optimistic concurrency
- `created_at`, `updated_at`

Use ordinary columns for stable, frequently queried fields. Use JSONB
for type-specific or evolving attributes. Exact field mapping and
requiredness must be finalized with the questionnaire schemas.

## 4. Invitations

### `ProjectInvitation`

Fields:

- `id`
- `project_id` — FK Project
- `created_by_id` — FK User
- `invited_email`
- `token_hash`
- `status` — `pending`, `accepted`, `revoked`, `expired`
- `expires_at`
- `accepted_by_id` — nullable FK User
- `accepted_at`
- `revoked_at`
- `created_at`

The invitation is bound to a normalized email address. The raw token is
returned only when the invitation is created; only its hash is stored.
Enforce at most one active invitation for a given project/email
combination.

## 5. Questionnaire

Questionnaire definitions live as versioned JSON files in the backend
repository. The database stores submissions and answers, not editable
questionnaire definitions.

### `QuestionnaireSubmission`

Fields:

- `id`
- `project_id` — FK Project
- `schema_key`
- `schema_version`
- `status` — at minimum `draft`, `submitted`, `correction_requested`
- `started_by_id` — FK User
- `submitted_by_id` — nullable FK User
- `started_at`
- `submitted_at`, nullable
- `supersedes_id` — nullable self-reference if revision history is
  implemented

### `QuestionnaireAnswer`

Fields:

- `id`
- `submission_id` — FK QuestionnaireSubmission
- `question_key`
- `value` — JSONB
- `origin` — `prefilled` or `customer`
- `is_confirmed`
- `updated_by_id` — FK User
- `updated_at`

Constraint: unique `(submission_id, question_key)`.

The exact resubmission/revision mechanism after a correction request
remains open. Preserve submitted answer data rather than silently
overwriting historical submissions.

## 6. Chat

### `Message`

Fields:

- `id`
- `project_id` — FK Project
- `sender_id` — FK User
- `content` — text
- `message_type` — extensible choice; initial type is ordinary text
- `client_message_id` — UUID supplied by client for idempotency
- `created_at`
- `updated_at`, nullable

Constraint: unique `(project_id, sender_id, client_message_id)` when a
client message ID is supplied.

Indexes: `(project_id, created_at)` and sender/project lookup as
required.

## 7. Documents

### `Document`

Fields:

- `id`
- `project_id` — FK Project
- `uploaded_by_id` — FK User
- `original_filename`
- `mime_type`
- `file_size` — BIGINT
- `checksum_sha256`
- `storage_key` — internal generated storage path/key
- `lifecycle_status` — `active`, `archive_pending`, `archived`,
  `deletion_pending`, `deleted`
- `processing_status` — `queued`, `processing`, `ready`, `failed`,
  `unsupported`
- `created_at`
- `archived_at`, nullable
- `deleted_at`, nullable

There is no document `visibility` field. All project documents are
shared with both participants.

### `DocumentChunk`

Fields: `id`, `document_id`, `chunk_index`, `content`, `page_number`,
`metadata` JSONB, `created_at`.

Constraint: unique `(document_id, chunk_index)`.

### `DocumentEmbedding`

Fields: `id`, `chunk_id`, `embedding_profile_key`, `model_name`,
`embedding` vector, `created_at`.

The active embedding profile must have a consistent vector dimension. A
model/dimension change requires re-embedding and a controlled index
rebuild or a separate versioned index. Do not mix incompatible vector
spaces in one search index.

### `DocumentLifecycleRequest`

Fields:

- `id`
- `document_id` — FK Document
- `action` — `archive` or `permanent_delete`
- `initiated_by_id` — FK User
- `status` — `pending`, `approved`, `rejected`, `cancelled`, `completed`
- `deletion_after` — nullable timestamp
- `created_at`
- `completed_at`, nullable

### `DocumentLifecycleApproval`

Fields: `id`, `request_id`, `user_id`, `decision`, `decided_at`.

Constraint: unique `(request_id, user_id)`. The initiator’s approval is
recorded when the request is created. The other participant must
explicitly approve.

## 8. Project State

All Project State entities are visible to both project participants.
Only the executor can create or modify structured Project State records.

### `ProjectStage`

Fields: `id`, `project_id`, `name`, `description`, `position`, `status`,
`start_date`, `due_date`, `created_by_id`, `created_at`, `updated_at`.

### `Requirement`

Fields: `id`, `project_id`, `title`, `description`, `status`,
`created_by_id`, `confirmed_by_id`, `confirmed_at`, `created_at`,
`updated_at`.

### `OpenQuestion`

Fields: `id`, `project_id`, `question`, `answer`, `status`,
`created_by_id`, `resolved_at`, `created_at`, `updated_at`.

### `ProjectConflict`

Fields: `id`, `project_id`, `title`, `description`, `status`,
`resolution`, `resolved_by_id`, `created_at`, `updated_at`.

A conflict preserves the competing values and their sources. AI-detected
conflicts first appear as private AI proposals; they become shared
Project State only after executor approval. Deterministic questionnaire
conflicts are recorded for executor review without silently replacing
passport values.

### `Task`

Fields: `id`, `project_id`, `stage_id` nullable FK ProjectStage,
`title`, `description`, `status`, `assignee_id` nullable FK User,
`due_date`, `created_by_id`, `created_at`, `updated_at`.

No percentage completion field is defined.

### `Evidence`

Fields: `id`, `project_id`, `source_type`, `source_id`, `excerpt`,
`metadata` JSONB, `created_at`.

`source_type` identifies a supported source such as a message,
questionnaire answer, document chunk, or manual note. `source_id` is a
polymorphic UUID; the application must validate that the referenced
source exists and belongs to the same project. A plain polymorphic UUID
cannot be protected by a normal database foreign key.

### Evidence links

- `AIProposalEvidence`: link table between AIProposal and Evidence.
- `ProjectConflictEvidence`: link table between ProjectConflict and
  Evidence.

Both link tables should enforce unique pairs.

## 9. AI Assistant

### `AIModelProfile`

Fields:

- `id`
- `task_key` — unique task/profile key
- `provider_key`
- `model_name`
- `capabilities` JSONB
- `parameters` JSONB
- `fallback_profile_id` — nullable self-reference
- `is_enabled`
- `config_version`
- `updated_at`

Provider credentials are not stored here. Store secret references or
configuration identifiers only; actual secrets belong in environment
configuration or a secret manager.

Initial task keys include:

- `message_analysis`
- `conversation_analysis`
- `contradiction_detection`
- `document_embedding`
- `rag_reranking`
- `specification_generation`

### `AIAnalysisRun`

Fields:

- `id`
- `project_id` — FK Project
- `profile_id` — nullable FK AIModelProfile
- `task_key`
- `trigger_type`
- `provider_key`
- `model_name`
- `profile_version`
- `prompt_version`
- `input_hash`
- `status`
- `input_tokens`, nullable
- `output_tokens`, nullable
- `estimated_cost`, nullable decimal
- `error_code`, nullable
- `started_at`
- `completed_at`, nullable

Store execution metadata and source references. Do not retain full
prompts or complete sensitive source content by default.

### `AIProposal`

Fields:

- `id`
- `project_id` — FK Project
- `analysis_run_id` — FK AIAnalysisRun
- `proposal_type`
- `title`
- `description`
- `rationale`
- `proposed_payload` JSONB
- `final_payload` JSONB, nullable
- `status` — `pending`, `accepted`, `rejected`, `applied`, `failed`
- `reviewed_by_id` — nullable FK User
- `reviewed_at`, nullable
- `applied_at`, nullable
- `created_at`

AI proposals and analysis records are private to the executor. They are
not included in the customer-facing Project State response.

### `AIProposalEvidence`

Fields: `id`, `proposal_id`, `evidence_id`, `created_at`.

Constraint: unique `(proposal_id, evidence_id)`.

## 10. Specifications and audit

### `Specification`

One-to-one with Project.

Fields: `id`, `project_id`, `content`, `status`, `updated_by_id`,
`version`, `created_at`, `updated_at`.

Formal approval, comments, and full version comparison are deferred.

### `ProjectAuditLog`

Fields: `id`, `project_id`, `actor_id` nullable, `action`,
`target_type`, `target_id`, `metadata` JSONB, `created_at`.

Audit metadata must not contain passwords, raw invitation tokens, API
keys, or unnecessary document/message content.

## 11. Relationship summary

- User to Project: many-to-many through ProjectMember.
- Project to ProjectPassport: one-to-one.
- Project to ProjectInvitation: one-to-many.
- Project to QuestionnaireSubmission: one-to-many.
- QuestionnaireSubmission to QuestionnaireAnswer: one-to-many.
- Project to Message: one-to-many.
- Project to Document: one-to-many.
- Document to DocumentChunk: one-to-many.
- DocumentChunk to DocumentEmbedding: one-to-many across profile/version
  changes.
- Document to DocumentLifecycleRequest: one-to-many.
- DocumentLifecycleRequest to DocumentLifecycleApproval: one-to-many.
- Project to each Project State entity: one-to-many.
- Project to Evidence: one-to-many.
- Project to AIAnalysisRun: one-to-many.
- AIAnalysisRun to AIProposal: one-to-many.
- AIProposal to Evidence: many-to-many through AIProposalEvidence.
- Project to Specification: one-to-one.
- Project to ProjectAuditLog: one-to-many.

## 12. Migration gate

Before creating production migrations, finalize:

- required/nullable fields and defaults;
- exact status choices and transitions;
- questionnaire revision strategy;
- exact passport-to-questionnaire mapping;
- deletion and retention constraints;
- embedding model and vector dimension;
- indexes based on actual query patterns;
- project and account deletion policy.
