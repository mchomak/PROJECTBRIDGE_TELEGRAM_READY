# ProjectBridge — Open Decisions

**Purpose:** Track decisions that remain unresolved after the
architecture discussion.  
**Last updated:** 2026-11-11

The items below must be resolved before the corresponding implementation
is considered complete. They are not permission to invent product
behavior silently.

## Product and workflow

1.  **Questionnaire correction flow:** Decide whether a correction
    request reopens the same submission or creates a superseding
    submission. Preserve the original submitted answers either way.
2.  **Questionnaire schemas:** Define the exact questions, branching
    rules, required fields, and schema versions for all four project
    types.
3.  **Passport mapping:** Define the exact mapping from each
    questionnaire answer to passport fields, including conflict
    detection rules and which value remains authoritative until executor
    review.
4.  **Project lifecycle:** Define whether completed or archived projects
    can be reopened and which operations remain available.
5.  **Project State statuses:** Finalize status choices and allowed
    transitions for stages, requirements, tasks, open questions, and
    conflicts.
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
19. **Questionnaire conflict visibility:** Confirm whether deterministic
    questionnaire conflicts appear immediately in shared Project State
    or remain in an executor review queue until resolved.

## API and implementation

20. **Pagination defaults:** Set page sizes and cursor behavior.
21. **Rate limits:** Set limits for authentication, invitations,
    uploads, chat, and AI actions.
22. **Idempotency storage:** Define key scope and retention for
    `Idempotency-Key`.
23. **Optimistic concurrency:** Define which resources use version
    checks beyond passport and specification.
24. **API response schemas:** Finalize serializer fields and error codes
    for every endpoint.
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
32. **Closed-project retention:** Define the notification and decision
    process before the proposed 12-month retention period expires.
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
