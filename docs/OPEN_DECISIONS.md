# ProjectBridge — Open Decisions

**Purpose:** Track decisions that remain unresolved after the
architecture discussion.  
**Last updated:** 2026-11-13

Items not marked resolved must be resolved before the corresponding
implementation is considered complete. Resolved entries remain here as
decision history; they are not permission to invent product behavior
silently.

## Product and workflow

1.  **Questionnaire correction flow — resolved for the MVP on
    2026-11-12:** A correction request changes the submitted row to
    `correction_requested` without changing its answers and creates one
    new `draft` with `supersedes_id` pointing to the source. The new draft
    copies the source answers and schema version. Repeating the request
    returns the existing draft. See the Stage 04–08 Autopilot spec §3.7
    and `database/DATA_MODEL.md`.
2.  **Questionnaire schemas — resolved for the MVP on 2026-11-12:** The
    product-authored v1 JSON files cover `website`, `telegram_bot`,
    `automation`, and `other`. Required common fields are `goal`,
    `target_audience`, `expected_result`, `functional_scope`, and
    `has_integrations`. `integrations` is required and non-empty when
    enabled and is stored as `[]` when disabled. Optional fields are
    `constraints`, `deadline`, `budget_min`, `budget_max`, and `currency`;
    currency is required when a budget is present and the minimum cannot
    exceed the maximum. Website and Telegram bot schemas conditionally
    require an HTTP(S) existing-resource URL; automation branches on
    `scheduled|event|manual`; `other` requires `project_area`. Published
    versions are immutable; new drafts select the latest version, while
    corrections retain their source version. See the versioned JSON in
    `backend/apps/questionnaire/schemas/` and Stage 04–08 Autopilot spec
    §3.2–3.4.
3.  **Passport mapping (Stage 05) — resolved for the MVP on 2026-11-12:**
    `goal`, `target_audience`, `expected_result`, `deadline`,
    `budget_min`, `budget_max`, and `currency` map to same-named passport
    fields. `functional_scope`, `integrations`, and `constraints` map
    under the project-type key in their respective JSON fields;
    integrations use `{enabled, items}`. Type-specific answers and schema
    version are preserved in `additional_data.questionnaire`. Optional
    empty values do not clear the passport. Differing values are kept in
    an executor-only questionnaire conflict queue; the passport remains
    unchanged until the executor chooses `keep_passport` or `apply_answer`.
    No automatic shared `ProjectConflict` is created. See Stage 04–08
    Autopilot spec §3.5–3.6 and `database/DATA_MODEL.md`.
4.  **Project lifecycle — resolved for the MVP on 2026-11-11:** New
    projects start as `draft`; accepting a customer invitation moves a
    draft project to `active`. The executor may move `active` to
    `completed`, reopen `completed` to `active`, archive `draft`, `active`,
    or `completed`, and restore `archived` to its saved prior status.
    `status_before_archive` is saved only while archived and cleared on
    restore. Completed projects are read-only except for executor reopen
    and archive actions. Archived projects are read-only except for
    executor restore, are listed separately, and are not deleted.
    See `product/MVP_SCOPE.md`, `database/DATA_MODEL.md`,
    `api/API_CONTRACT.md`, and `security/ACCESS_CONTROL_AND_SECURITY.md`.
5.  **Project State statuses — resolved for the MVP on 2026-11-12:**
    `ProjectStage`: `planned -> active|cancelled`,
    `active -> blocked|completed|cancelled`,
    `blocked -> active|cancelled`; `Requirement`: `draft ->
    confirmed|rejected`, `confirmed -> in_progress|rejected`,
    `in_progress -> blocked|completed|rejected`,
    `blocked -> in_progress|rejected`; `Task`: `todo ->
    in_progress|cancelled`, `in_progress -> blocked|done|cancelled`,
    `blocked -> in_progress|cancelled`; `OpenQuestion`: `open ->
    resolved|dismissed`; `ProjectConflict`: `unresolved ->
    resolved|dismissed`. Completed, cancelled, rejected, resolved, and
    dismissed states are terminal. Project State owns transition
    validation; no generic workflow engine or completion percentage is
    introduced. See ADR-012 and the Stage 04-08 Autopilot spec §3.
6.  **Customer contribution:** Confirm whether any structured customer
    edits beyond questionnaire submission will ever be allowed in the
    MVP.
7.  **Specification scope:** Confirm generation inputs, output format,
    editing behavior, and whether a specification draft is mandatory for
    MVP acceptance.
8.  **Chat scope:** Decide whether message editing, deletion,
    attachments, read receipts, and typing indicators are excluded.
9.  **Account lifecycle:** Define account deactivation/deletion and
    behavior when a user belongs to active projects.

## AI and RAG

10. **Providers and models — resolved for Stage 10 on 2026-11-13:**
    OpenAI is the initial provider. `message_analysis` uses
    `gpt-6-luna` with `gpt-6.1-sol` fallback;
    `conversation_analysis`, `contradiction_detection`, and
    `specification_generation` use `gpt-6.1-sol` with `gpt-6-luna`
    fallback; `document_embedding` uses `text-embedding-3-small` at 1536
    dimensions; `rag_reranking` uses strict structured scoring with
    `gpt-6.1-sol` and `gpt-6-luna` fallback. Credentials remain in
    `OPENAI_API_KEY`; a model denied or unavailable to an account returns
    a normalized provider error. Model identifiers and Responses API
    structured-output support were checked against the official [GPT-6
    Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) and
    [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
    catalogs on 2026-11-13. See ADR-016.
11. **Embedding dimension — resolved for Stage 09 on 2026-11-13:** The
    initial `document_embedding` profile uses OpenAI
    `text-embedding-3-small` with 1536 dimensions. Credentials remain
    external configuration and are not required for local tests.
12. **Embedding migration — resolved for Stage 09 on 2026-11-13:**
    Vector identity is provider + exact model identifier + dimensions,
    with a separate `embedding_space_version`; routing `config_version`
    changes do not hide vectors. Same-dimension model changes require a
    maintenance window and reprocessing all eligible documents before
    retrieval resumes. Stage 10 has no shadow index or atomic cutover.
    Dimension changes require a versioned shadow column or table, verified
    backfill, and explicit cutover. The active search never mixes spaces.
13. **Chunking — resolved for Stage 09 on 2026-11-13:** Chunks are at
    most 1000 Unicode characters with 150 characters overlap. PDF chunks
    do not cross pages, DOCX chunks do not cross paragraphs or table
    cells, and text or Markdown chunks record character offsets. Chunk
    rows have stable per-document ordering and source metadata.
14. **Retrieval — resolved for Stage 09 on 2026-11-13:** Use cosine
    distance and return five nearest chunks by default, with a maximum of
    20. Require active project membership, filter to the current project
    and active/ready documents, and require an exact embedding-space
    key/version/model match. Stage 10 provides a real reranking capability,
    but Stage 09 retrieval does not invoke it automatically.
15. **Fallback — resolved for Stage 10 on 2026-11-13:** Retry transient
    rate-limit, connection, timeout, and server errors once. Only then
    try an enabled fallback that serves the same task and required
    capability. Embedding fallback must use the identical provider,
    model, dimensions, and `embedding_space_version`; unrelated models
    never share a vector slice. Never fallback for missing credentials,
    authentication/permission errors, invalid requests, or unavailable
    models. Provider timeout is configured per profile (30–60 seconds).
16. **Triggers:** Finalize which events trigger automatic AI analysis
    and the debounce/batching policy for chat messages.
17. **Cost controls — resolved for Stage 10 on 2026-11-13:** Seeded
    profile defaults reserve up to USD 1.00 per task per UTC day, USD
    0.25 per generation or reranking request, and USD 0.10 per embedding
    request. A PostgreSQL task-scoped lock serializes reservations across
    profiles, and fallback budget is reserved before the fallback API call.
    Profiles cap input size, candidate count, output tokens, and timeout.
    Usage records store actual token counts and estimated cost when supplied. The
    estimates use editable profile rate snapshots. This does not cap
    billing outside ProjectBridge or replace provider-side account
    limits. See ADR-016.
18. **Prompt/version management — resolved for Stage 10 on 2026-11-13:**
    Callers provide a version label for each text-generation prompt.
    The router stores the label and SHA-256 of inputs, not prompts or
    source text. Prompt templates remain versioned alongside the
    domain code and are tested by their owning stages. See ADR-016.
19. **Questionnaire conflict visibility — resolved for the MVP on
    2026-11-12:** Deterministic questionnaire conflicts remain in an
    executor-only review queue until resolved. They do not appear as
    shared Project State conflicts. See Stage 04–08 Autopilot spec §3.6.

## API and implementation

20. **Pagination defaults:** Set page sizes and cursor behavior for the
    remaining collections. Chat history is resolved for Stage 07 on
    2026-11-12: signed cursors use stable `(created_at, id)` ordering,
    newest first, with a default page size of 50 and maximum of 100. See
    `api/API_CONTRACT.md`.
21. **Rate limits — invitation and chat scopes resolved for Stage 04
    and Stage 07 on 2026-11-12:** Invitation creation is limited to
    20/hour/executor,
    preview to 30/hour/IP, and acceptance to 10/hour/user through the
    shared Redis cache. See ADR-011. New chat submissions are limited to
    60 per user per fixed UTC minute through one Redis counter and are
    submitted through REST; WebSocket is delivery-only. Upload and AI
    action limits remain open. Stage 02
    authentication scopes remain
    `register` 5/hour, `login` 10/minute, `resend` 3/hour, and `confirm`
    10/hour through the shared cache.
22. **Idempotency storage:** Define key scope and retention for
    `Idempotency-Key`.
23. **Optimistic concurrency:** Define which resources use version
    checks beyond passport and specification.
24. **API response schemas:** Finalize serializer fields and error codes
    for remaining endpoints. Stage 04 invitation list/create/revoke
    schemas and error codes are defined in `api/API_CONTRACT.md`.
25. **Password reset:** Define the reset flow.
26. **Document parser libraries — resolved for Stage 09 on 2026-11-13:**
    Pin pypdf 5.4.0 for PDF and python-docx 1.1.2 for DOCX. Decode TXT
    and Markdown as UTF-8, UTF-16, or UTF-32 with a BOM; other encodings
    fail visibly instead of being guessed.
27. **Scanned PDFs — resolved for Stage 09 on 2026-11-13:** A valid PDF
    with no extractable text layer is marked `unsupported`; a malformed
    PDF is marked `failed`. OCR remains out of scope.
28. **Malware scanning:** Select a scanner and deployment approach
    before public production.

## Security, retention, and compliance

29. **Privacy and consent:** Implement appropriate privacy notices and
    consent/legal basis for personal-data processing before public
    customer onboarding.
30. **External AI disclosure:** Review each provider’s data processing,
    retention, and training terms; disclose external processing as
    required before production.
31. **Operational log retention:** Set an exact retention period for
    non-content AI and application logs.
32. **Closed-project retention — resolved for the MVP on 2026-11-11:**
    Completed and archived projects are not automatically deleted. The
    previously proposed 12-month project-retention and 14-day backup
    periods are not approved product requirements. A future product
    retention policy and operational backup schedule remain undecided.
    A mutually approved document deletion is a separate document-level
    action and does not delete its project or other project data.
33. **Backup restoration:** Define recovery objectives and schedule
    restore tests.
34. **Production secret manager:** Select the deployment platform and
    secret-management mechanism.

## Infrastructure and release

35. **Hosting:** Select production hosting and deployment topology.
36. **Monitoring:** Select error tracking, metrics, logs, and alerting
    tools.
37. **Email provider:** Select production email delivery provider.
38. **Object storage:** Select S3-compatible storage provider when
    moving beyond local development.
39. **CI pipeline:** Define test, lint, type-check, migration-check, and
    deployment stages.
40. **MVP acceptance tests:** Convert the product workflows into
    end-to-end acceptance scenarios.

## Recently resolved document lifecycle decision

41. **Document archive and deletion lifecycle — resolved for the MVP on
    2026-11-12:** Archive requests require both active project roles;
    rejection returns the document to `active`, and approval moves it to
    `archived`. Permanent deletion starts only from `archived`; its
    30-day cancellation window begins at the second approval. Either
    active member may cancel strictly before the deadline, returning the
    document to `archived`; restore is a separate action. New requests,
    decisions, and restore require a `draft` or `active` project. An
    already approved due deletion still completes after a project
    completes or is archived, and cancellation remains available before
    the deadline. Backup expiry remains operational and has no fixed
    product promise. See ADR-013, `documents/DOCUMENT_LIFECYCLE.md`,
    `database/DATA_MODEL.md`, `api/API_CONTRACT.md`, and
    `security/ACCESS_CONTROL_AND_SECURITY.md`.
42. **Restore during a pending deletion request — resolved for the MVP on
    2026-11-12:** Restoring an archived document cancels a permanent-delete
    request that has only its initiator's approval, because that unfinished
    consent must not remain actionable or block a later request. An
    already approved deletion remains in `deletion_pending` and requires
    the existing explicit cancellation before restore. See ADR-013 and
    the document lifecycle, data model, API, and security contracts.
