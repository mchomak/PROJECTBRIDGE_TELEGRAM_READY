# ProjectBridge Database Model

**Status:** Logical model baseline; detailed field constraints must be
finalized before migrations  
**Database:** PostgreSQL  
**Last updated:** 2026-11-12

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
- Vector search: pgvector. The initial `text-embedding-3-small` profile
  uses 1536 dimensions and cosine HNSW indexing. Dimension changes need
  a versioned shadow column/table and completed backfill before cutover.

## 2. Accounts

### `User`

| Field               | Type / rule          | Notes                                    |
|:--------------------|:---------------------|:-----------------------------------------|
| `id`                | UUID, PK             | User identifier                          |
| `email`             | Unique email         | Login identifier; trim and casefold before validation and storage |
| `password`          | Django password hash | Never store plaintext                    |
| `first_name`        | String, optional     | Blank value is `""`                      |
| `last_name`         | String, optional     | Blank value is `""`                      |
| `email_verified_at` | Nullable timestamp   | Null until verified                      |
| `is_active`         | Boolean              | Django account activation                |
| `created_at`        | Timestamp            | Creation time                            |
| `updated_at`        | Timestamp            | Last update                              |

The Django model is `accounts.User` (Python package
`apps.accounts`), based on `AbstractUser` with UUID primary key, unique
email login, and an email-only manager. Set
`AUTH_USER_MODEL = "accounts.User"`. The manager trims and applies
Unicode `casefold()` to the full email address before uniqueness checks
and storage. This intentionally treats the full address as
case-insensitive.

Password changes use Django's password hashing and validators. The
preferred configured hasher is Argon2; PBKDF2 remains enabled to read
compatible existing Django hashes. First and last names are optional
and blank by default.

### `EmailVerificationToken`

Fields: `id`, `user_id`, `token_hash`, `expires_at`, `used_at`,
`created_at`.

Store only a hash of the verification token. Enforce single use and
expiration. Stage 02 uses a SHA-256 hex digest, a 24-hour lifetime, and
one active token per user. Reissuing a token marks the previous token
used before creating the replacement.

### Stage 02 migration plan

Stage 01 applied Django's existing `auth` migrations and
`common.0001_enable_pgvector` before the account model was introduced.
Stage 02 adds `accounts.0001_initial`, dependent on
`auth.0012_alter_user_first_name_max_length`, to create `accounts_user`
and `accounts_emailverificationtoken`. It does not edit or replace any
existing migration or move rows. An existing Stage 01 database retains
its legacy `auth_user` table unchanged; a clean database migrated with
`AUTH_USER_MODEL` already configured does not create that legacy table.
Verify the additive migration on both a separately created empty
database and the existing local database without clearing data or
volumes. Future user relations must refer to
`settings.AUTH_USER_MODEL`.

Account deactivation/deletion and password reset remain open decisions
and are outside Stage 02.

## 3. Projects and membership

### `Project`

Fields:

- `id` — UUID, PK
- `name` — string
- `description` — text, nullable
- `project_type` — choice: `website`, `telegram_bot`, `automation`,
  `other`
- `status` — choice: `draft`, `active`, `completed`, `archived`
- `status_before_archive` — nullable choice: `draft`, `active`,
  `completed`; populated only while the project is archived
- `created_by_id` — FK to User
- `created_at`, `updated_at`
- `completed_at`, nullable
- `archived_at`, nullable

Lifecycle transitions:

| From | To | Actor or trigger |
|:-----|:---|:-----------------|
| New project | `draft` | Project creation |
| `draft` | `active` | Successful customer invitation acceptance; the invitation service applies this transition |
| `active` | `completed` | Executor completes the project |
| `completed` | `active` | Executor reopens the project |
| `draft`, `active`, `completed` | `archived` | Executor archives the project; save the current status in `status_before_archive` |
| `archived` | `status_before_archive` | Executor restores the project; clear `status_before_archive` |

Only executor actions can directly change project status. The
`draft`-to-`active` transition is a system-side effect of a valid
customer invitation acceptance, not a client-supplied status update.
Require `status_before_archive` while `status` is `archived`, and require
it to be null for every other status. Project status changes do not
revoke memberships or delete project data. Archive is reversible state,
not deletion.
Set `completed_at` when a project is completed. Set `archived_at` when it
is archived and clear `archived_at` when it is restored.

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

The field names and types above are the approved Stage 03 passport
schema. Do not add or remove business fields. Use ordinary columns for
stable, frequently queried fields and JSONB for type-specific or evolving
attributes. Stage 05 has explicitly defined the questionnaire mapping
and validation rules below; they are not inferred from passport field
types.

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
email-link-only and is never included in the invitation API response;
only its hash is stored.
Enforce at most one active invitation for a given project/email
combination.

`invited_email` uses the existing accounts normalization rule (trim and
case-fold). `token_hash` is a unique SHA-256 hex digest. New invitations
expire seven days after creation. A pending invitation whose expiry has
passed is moved to `expired` when the executor lists invitations or
attempts to invite that email again. A partial unique constraint permits
at most one `pending` invitation per project and normalized email.

The raw token is sent only in the outbound invitation link, in the URL
fragment. It is absent from the API response, database, application logs,
and project audit metadata. An active customer membership prevents another
invitation for the project; the existing project membership constraint
continues to enforce one active customer.

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
- `passport_version` — passport concurrency token captured when the draft starts
- `status` — `draft`, `submitted`, or `correction_requested`
- `started_by_id` — FK User
- `submitted_by_id` — nullable FK User
- `started_at`
- `submitted_at`, nullable
- `supersedes_id` — nullable self-reference to the submission that this
  correction draft replaces

Constraint: at most one `draft` questionnaire submission exists per
project. A correction request changes the original submitted row to
`correction_requested` and creates a new draft that references it with
`supersedes_id`; the original submission and answers are retained. A
repeated correction request returns the already-created draft.

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

Prefilled answers use `origin=prefilled` and `is_confirmed=false`.
Editing an answer changes its origin to `customer`. Saving a draft writes
answers only to `QuestionnaireAnswer`; it does not mutate
`ProjectPassport`. Inactive-branch answers are removed or rejected.
Submitting a complete draft requires an explicit customer confirmation if
any prefilled answer is still unconfirmed. A successful submission locks
the answer rows and records the submitting actor and time. If the passport
version no longer matches `passport_version`, the transaction rolls back
and the draft stays editable.

### `QuestionnaireConflict`

Fields:

- `id`
- `submission_id` — FK QuestionnaireSubmission
- `answer_id` — FK QuestionnaireAnswer
- `mapped_field` — explicit passport path, such as `goal` or
  `functional_scope.website`
- `passport_value` — immutable JSON snapshot at submission
- `answer_value` — immutable JSON snapshot from the submitted answer
- `status` — `pending` or `resolved`
- `decision` — nullable `keep_passport` or `apply_answer`
- `reviewed_by_id` — nullable executor FK User
- `created_at`
- `resolved_at`, nullable

Constraint: one conflict per answer. Pending conflicts are visible only to
active project executors. Resolution checks the current passport version
and the affected field against the stored passport snapshot. `keep_passport`
does not write the passport; `apply_answer` writes the stored answer value
through `projects.services.update_passport`. Audit metadata contains the
actor, mapped field names, decision, and version transition, never answer
or passport contents. AI cannot resolve these deterministic conflicts.

### Version 1 schema and validation decisions

The immutable, product-authored files are
`backend/apps/questionnaire/schemas/{website,telegram_bot,automation,other}.v1.json`.
New drafts use the latest version for their project type. A correction
draft retains the source submission's version. Add a new version file
instead of changing a published schema.

All project types require `goal`, `target_audience`, `expected_result`,
`functional_scope`, and `has_integrations`. When integrations are
enabled, `integrations` requires at least one item; when disabled, the
stored value is an empty list. Optional common fields are `constraints`,
`deadline`, `budget_min`, `budget_max`, and `currency`. A supplied budget
requires a three-letter currency code, and `budget_min` cannot exceed
`budget_max`. Dates use `YYYY-MM-DD`; resource URLs use HTTP(S).

Type-specific branches are deterministic: `website` requires
`has_existing_site` and requires `existing_site_url` when true;
`telegram_bot` requires `has_existing_bot` and conditionally
`existing_bot_url`; `automation` requires `trigger_type` (`scheduled`,
`event`, or `manual`) and conditionally `schedule_details` or
`event_source`; `other` requires `project_area`. The backend rejects
unknown answers, invalid values, and answers for inactive branches.

The approved mappings are:

| Questionnaire answer | Passport path | Empty/equal/different value behavior |
|:--|:--|:--|
| `goal` | `goal` | Empty is skipped; equal is a no-op; a different existing value becomes a conflict. |
| `target_audience` | `target_audience` | Empty is skipped; equal is a no-op; a different existing value becomes a conflict. |
| `expected_result` | `expected_result` | Empty is skipped; equal is a no-op; a different existing value becomes a conflict. |
| `deadline` | `deadline` | Empty is skipped; dates are stored as dates; equal is a no-op; a different existing date becomes a conflict. |
| `budget_min` | `budget_min` | Empty is skipped; decimals are stored as decimals; equal is a no-op; a different existing amount becomes a conflict. |
| `budget_max` | `budget_max` | Empty is skipped; decimals are stored as decimals; equal is a no-op; a different existing amount becomes a conflict. |
| `currency` | `currency` | Empty is skipped; equal is a no-op; a different existing currency becomes a conflict. |
| `functional_scope` | `functional_scope[project_type]` | Empty is skipped; equal is a no-op; a different existing value becomes a conflict. |
| `constraints` | `constraints[project_type]` | Empty is skipped; equal is a no-op; a different existing value becomes a conflict. |
| `has_integrations` plus `integrations` | `integrations[project_type] = {enabled, items}` | An explicit disabled answer stores `{enabled: false, items: []}`; equal is a no-op; a different existing object becomes a conflict. |
| Type-specific non-control answers | `additional_data.questionnaire[project_type].answers[key]` | Non-empty answers are retained under their question key; empty answers are skipped. |
| Schema version | `additional_data.questionnaire[project_type].schema_version` | The submitted immutable schema version is stored with the type-specific answers. |
| `has_existing_site`, `has_existing_bot` | — | Branch control answers are not mapped. |

An empty passport path is populated, an equal non-empty value is left
unchanged, and a different non-empty value creates a
`QuestionnaireConflict`. Empty optional answers never clear passport data.
The questionnaire service submits the complete versioned change set to
`projects.services.apply_questionnaire_mapping(project_id, actor,
expected_version, mapped_changes)`. That projects-owned service locks and
updates the passport and its audit row atomically. Questionnaire code
never writes `ProjectPassport` directly. The submission, answer
confirmation, conflict snapshots, and passport mapping share one
transaction; stale passport versions roll back all of them. Conflicts
remain executor-only and are not shared Project State.

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

`content` is trimmed at the API boundary, must not be blank, and is
limited to 10,000 characters. `client_message_id` is required.
Constraint: unique `(project_id, sender_id, client_message_id)`.

Index: `(project_id, created_at, id)` supports stable cursor history.
Messages are ordered by `(created_at, id)`. The initial `message_type`
is `text`; editing and deletion are outside this stage.

## 7. Documents

### `Document`

Fields:

- `id`
- `project_id` — FK Project
- `uploaded_by_id` — FK User
- `original_filename`
- `mime_type` — derived by the server from validated content and extension
- `file_size` — nonnegative BIGINT, at most `20 * 1024 * 1024` bytes
- `checksum_sha256` — server-computed lowercase SHA-256 hex digest
- `storage_key` — unique internal UUID-based key; independent of the
  display filename and never returned by the API
- `lifecycle_status` — `active`, `archive_pending`, `archived`,
  `deletion_pending`, `deleted`
- `processing_status` — `queued`, `processing`, `ready`, `failed`,
  `unsupported`
- `processing_generation` is an internal fencing counter incremented each
  time a worker claims processing; only the current generation can publish
  derived chunks and embeddings
- `created_at`
- `archived_at`, nullable
- `deleted_at`, nullable

There is no document `visibility` field. All project documents are
shared with both participants.

The database stores metadata and lifecycle rows only. File bytes are
stored through Django's default storage on the persistent local media
volume. Upload creates the document with `processing_status=queued`;
Stage 09 owns extraction and subsequent processing transitions.
Lifecycle is an archive-first state machine. Archive requests may start
only for `active` documents and move them to `archive_pending` until the
other active participant approves or rejects. Approval moves the
document to `archived`; rejection returns it to `active`. Permanent
deletion requests may start only for `archived` documents. The document
stays archived until the second participant approves, then becomes
`deletion_pending` and receives a `deletion_after` deadline exactly 30
days from that second approval. Cancellation before the deadline returns
it to `archived`; the deadline is exclusive. Restore is a separate
transition from `archived` to `active`. If a permanent-delete request is
still pending with only the initiator's approval, restore marks that
request `cancelled` in the same transaction; a request already approved
by both participants must be explicitly cancelled before restoration.

When a due deletion completes, storage bytes and existing derivatives
are removed. The `Document` row remains with `lifecycle_status=deleted`,
`deleted_at`, an empty original filename/MIME type, zero size, and the
SHA-256 digest of empty content. Its internal storage key remains unique
and is never exposed. Lifecycle request/approval rows and one
content-free `ProjectAuditLog` event preserve the minimal consent and
deletion audit trail. No deleted content is written to audit metadata.

### `DocumentChunk`

Fields: `id`, `document_id`, `chunk_index`, `content`, nullable
`page_number`, `metadata` JSONB, `created_at`. Text chunks are at most
1000 Unicode characters with 150 characters of overlap. PDF metadata
records character offsets within the page; DOCX body paragraphs record
paragraph index and offsets, while table paragraphs record table, row,
cell, paragraph indexes, and offsets; TXT/Markdown metadata records
document character offsets.

Constraint: unique `(document_id, chunk_index)`.

### `DocumentEmbedding`

Fields: `id`, `chunk_id`, `embedding_profile_key`,
`embedding_profile_version`, `model_name`, `embedding` vector(1536),
`created_at`.

`embedding_profile_key` stores the stable embedding-space key derived from
provider, exact model identifier, and dimensions; it is not the routing
profile's admin key. `embedding_profile_version` stores the independent
`AIModelProfile.embedding_space_version`, not `config_version`. Timeout,
rate, or fallback configuration changes therefore leave existing vectors
queryable. Retrieval filters on the exact space-key/version/returned-model
tuple so same-dimension but different-model vectors are never mixed.

The MVP index uses a cosine HNSW index and a unique
`(chunk_id, embedding_profile_key, embedding_profile_version, model_name)`
key. The processor replaces a document's chunks during reprocessing, so a
model change currently requires a maintenance window: pause retrieval,
change the active profile, and run
`python manage.py reindex_document_embeddings --project-id <uuid>` or use
`--all-projects` for a deliberate full maintenance. The command queues the
documents-owned retry-safe reindex task for active and archived documents,
excluding lifecycle-pending, deleted, and unsupported documents. It does
not require editing document rows. Resume retrieval only when all eligible
documents are `ready` with embeddings in the new tuple. There is no
shadow-index or atomic cutover path. A dimension change requires a
versioned shadow column/table, completed backfill and verification, and an
explicit migration before switching.

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

Request statuses are `pending`, `approved`, `rejected`, `cancelled`, and
`completed`. Creation records an `approved` row for the initiator and
leaves the request `pending`. The other active participant’s decision
sets `approved` or `rejected`. For a permanent-delete request,
`deletion_after` is null until that second approval and is set to
approval time plus 30 days in the same transaction. Completion is
recorded only after the due sweep removes source data. Cancellation is
allowed only when the current time is strictly earlier than the deadline.

### `DocumentLifecycleApproval`

Fields: `id`, `request_id`, `user_id`, `decision`, `decided_at`.

Constraint: unique `(request_id, user_id)`. The initiator’s approval is
recorded when the request is created. The other participant must
explicitly approve.

## 8. Project State

All Project State entities are visible to active project participants.
Only the executor can create or modify structured Project State records,
and writes are allowed while the project is `draft` or `active`.

### `ProjectStage`

Fields: `id`, `project_id`, `name`, `description`, `position`, `status`,
`start_date`, `due_date`, `created_by_id`, `created_at`, `updated_at`.

Statuses are `planned`, `active`, `blocked`, `completed`, and
`cancelled`. Only transitions in ADR-012 are allowed; `completed` and
`cancelled` are terminal.

### `Requirement`

Fields: `id`, `project_id`, `title`, `description`, `status`,
`created_by_id`, `confirmed_by_id`, `confirmed_at`, `created_at`,
`updated_at`.

Statuses are `draft`, `confirmed`, `in_progress`, `blocked`, `completed`,
and `rejected`. Only transitions in ADR-012 are allowed; `completed` and
`rejected` are terminal.

### `OpenQuestion`

Fields: `id`, `project_id`, `question`, `answer`, `status`,
`created_by_id`, `resolved_at`, `created_at`, `updated_at`.

Statuses are `open`, `resolved`, and `dismissed`. Resolved and dismissed
questions are terminal.

### `ProjectConflict`

Fields: `id`, `project_id`, `title`, `description`, `status`,
`resolution`, `resolved_by_id`, `resolved_at`, `created_by_id`,
`created_at`, `updated_at`.

Statuses are `unresolved`, `resolved`, and `dismissed`. Resolving or
dismissing records the executor and time; both statuses are terminal and
cannot transition again. A resolved or dismissed conflict is immutable;
all later updates are rejected. A shared conflict requires at least two
same-project evidence sources and preserves their snapshots.

A conflict preserves the competing values and their sources. AI-detected
conflicts first appear as private AI proposals; they become shared
Project State only after executor approval. Deterministic questionnaire
conflicts are recorded for executor review without silently replacing
passport values.

### `Task`

Fields: `id`, `project_id`, `stage_id` nullable FK ProjectStage,
`title`, `description`, `status`, `assignee_id` nullable FK User,
`due_date`, `created_by_id`, `created_at`, `updated_at`.

Statuses are `todo`, `in_progress`, `blocked`, `done`, and `cancelled`.
Only transitions in ADR-012 are allowed; `done` and `cancelled` are
terminal. No percentage completion field is defined.

### `Evidence`

Fields: `id`, `project_id`, `source_type`, `source_id`, `excerpt`,
`metadata` JSONB, `created_at`.

`source_type` is `questionnaire_answer` or `message`. `source_id` is a
polymorphic UUID; the owning app's selector must validate that the
referenced source exists and belongs to the same project. Questionnaire
answers are resolved by the questionnaire selector and messages by the
chat selector. A plain polymorphic UUID cannot be protected by a normal
database foreign key. Evidence snapshots and conflict links are
immutable; a normal update or delete of Evidence is rejected.

### Evidence links

- `AIProposalEvidence`: link table between AIProposal and Evidence.
- `ProjectConflictEvidence`: link table between ProjectConflict and
  Evidence.

`ProjectConflictEvidence` enforces unique `(conflict_id, evidence_id)`
pairs. Deterministic questionnaire mapping conflicts remain in the
executor-only `QuestionnaireConflict` queue; they do not automatically
create a shared `ProjectConflict`.

## 9. AI Assistant

### `AIModelProfile`

Fields:

- `id`
- `profile_key` — unique profile identifier
- `task_key` — one of the six stable AI task keys
- `provider_key`
- `model_name`
- `capabilities` JSONB
- `parameters` JSONB
- `fallback_profile_id` — nullable self-reference
- `is_default` — the active profile for its task
- `is_enabled`
- `config_version`
- `embedding_space_version` вЂ” separate vector-space revision; only
  embedding results use it, not general profile/run configuration
- `updated_at`

Only one default profile may exist per task. Named non-default profiles
may be selected as a compatible fallback. Configuration edits increment
`config_version`.

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
- `attempt_count`
- `input_tokens`, nullable
- `output_tokens`, nullable
- `estimated_cost`, nullable decimal
- `reserved_cost` вЂ” cumulative conservative reservation across all attempts
- `request_budget_limit` вЂ” request-chain ceiling snapshotted from the
  primary profile; compatible fallbacks may lower it, never raise it
- `daily_budget_limit` вЂ” task-chain daily ceiling snapshotted from the
  primary profile; fallbacks cannot expand it
- `error_code`, nullable
- `started_at`
- `completed_at`, nullable

Store execution metadata and source references. Do not retain full
prompts or complete sensitive source content by default.

`project_id` is required for project-owned operations. Embedding
processing and retrieval include the owning project when calling the
router. Usage records contain hashes and metadata, never source text.
Each primary, retry, and fallback call reserves its maximum estimate before
execution under the task-scoped PostgreSQL lock. `reserved_cost` is never
reduced by successful usage reconciliation or a later failed attempt.

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
- deletion and retention constraints;
- versioned embedding migrations when changing the selected 1536-dimension
  `text-embedding-3-small` profile;
- indexes based on actual query patterns;
- project and account deletion policy.
