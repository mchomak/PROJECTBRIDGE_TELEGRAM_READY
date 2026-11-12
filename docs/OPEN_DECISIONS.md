# ProjectBridge — Open Decisions

**Purpose:** Track decisions that remain unresolved after the
architecture discussion.  
**Last updated:** 2026-11-12

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

10. **Providers and models:** Select initial providers and model
    identifiers for every task profile.
11. **Embedding dimension:** Select the first embedding model and vector
    dimension before finalizing pgvector migrations.
12. **Embedding migration:** Define the rollout procedure when the
    embedding model changes.
13. **Chunking:** Choose chunk size, overlap, metadata, and
    parser-specific rules.
14. **Retrieval:** Choose similarity metric, top-k, metadata filters,
    reranking policy, and thresholds.
15. **Fallback:** Define compatible fallback profiles, timeout behavior,
    and retry limits.
16. **Triggers:** Finalize which events trigger automatic AI analysis
    and the debounce/batching policy for chat messages.
17. **Cost controls:** Define per-task budgets, usage limits, and alert
    thresholds.
18. **Prompt/version management:** Define how prompt templates are
    versioned and tested.
19. **Questionnaire conflict visibility — resolved for the MVP on
    2026-11-12:** Deterministic questionnaire conflicts remain in an
    executor-only review queue until resolved. They do not appear as
    shared Project State conflicts. See Stage 04–08 Autopilot spec §3.6.

## API and implementation

20. **Pagination defaults:** Set page sizes and cursor behavior.
21. **Rate limits — invitation scopes resolved for Stage 04 on
    2026-11-12:** Invitation creation is limited to 20/hour/executor,
    preview to 30/hour/IP, and acceptance to 10/hour/user through the
    shared Redis cache. See ADR-011. Limits for uploads, chat, and AI
    actions remain open. Stage 02 authentication scopes remain
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
26. **Document parser libraries:** Select maintained PDF, DOCX, TXT, and
    Markdown parsers.
27. **Scanned PDFs:** Confirm user-facing behavior when a PDF contains
    no extractable text.
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
