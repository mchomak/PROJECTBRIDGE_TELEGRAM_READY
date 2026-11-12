# Graph Report - .  (2026-11-12)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1933 nodes · 5492 edges · 190 communities (123 shown, 67 thin omitted)
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 1256 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `87c6b74b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- questionnaire/api/views.py
- submit_submission
- project_state/services.py
- ErrorEnvelopeSerializer
- create_project
- ProjectStatePage.tsx
- CsrfSanitizingAPIView
- verification/views.py
- api/index.ts
- documentsApi.ts
- QuestionnairePage.tsx
- Спецификация: ProjectBridge, этапы 04–08
- devDependencies
- Stage 13: MVP Integration and Hardening
- chat/services.py
- ProjectOverviewPage.tsx
- invitations/services.py
- chat/api/views.py
- projects/services.py
- invitation/index.ts
- compilerOptions
- ChatPage.tsx
- Implementation interfaces and project rules
- biome.json
- sync.py
- test_chat_api.py
- test_auth.py
- ProjectChatConsumer
- test_project_state_api.py
- check_readiness
- Versioned REST, WebSocket, and OpenAPI Contract
- project_state/api/views.py
- Stage 01 Specification
- api_exception_handler
- test_questionnaire_submission_api.py
- Plan - ProjectBridge stages 04-08
- test_questionnaire_api.py
- App.tsx
- T01 - Issue and manage project invitations
- Technical Documentation Map
- common/tests/test_tasks.py
- run_production_process
- Project-Scoped Roles and Shared Project State
- schema.d.ts
- base.py
- AI Router
- T02 - Preview and accept project invitations
- Single ASGI HTTP and WebSocket Entry Point
- Stage 00 Specification
- Session-cookie authentication with CSRF protection
- Hashed single-use email verification tokens
- AccountsConfig
- AiAssistantConfig
- ChatConfig
- CommonConfig
- test_migrations.py
- DocumentsConfig
- HealthConfig
- InvitationsConfig
- ProjectStateConfig
- ProjectsConfig
- QuestionnaireConfig
- SpecificationsConfig
- Invitation Expiry and Rate Limits
- Relational Project Data Model
- Local Development and Operations Guide
- Persistent Local Data with Named Volumes
- Account model and migration plan
- Project API
- T03 - Build deterministic questionnaire schemas and drafts
- record_project_action
- T05 - Create and edit Project State records
- T06 - Expose shared Project State with evidence and conflict resolution
- accounts/api/__init__.py
- chat/migrations/0001_initial.py
- common/api/__init__.py
- 0001_enable_pgvector.py
- 0002_project_audit_log.py
- documents/migrations/0001_initial.py
- 0002_remove_document_document_file_size_positive.py
- invitations/migrations/0001_initial.py
- project_state/migrations/0001_initial.py
- projects/migrations/0001_initial.py
- 0002_project_constraints.py
- questionnaire/api/__init__.py
- questionnaire/migrations/0001_initial.py
- 0002_questionnairesubmission_passport_version_and_more.py
- schemas/__init__.py
- Separate Production Settings
- Additive Accounts User Migration
- Provider-Independent AI Configuration
- Vite Frontend Entry Document
- generate-api-types.mjs
- Stage 00 вЂ” Repository Baseline and Tooling
- Stage 00 Interfaces and Implementation Rules
- Stage 00 Requirements Manifest
- Stage 00 Reference
- Stage 01 вЂ” Application Skeleton and Local Runtime
- Stage 01 Handoff 01-1
- Stage 01 Implementation Boundaries
- Stage 01 Requirement Manifest
- Stage 01 Backend Ticket
- Stage 01 Frontend Shell Ticket
- Stage 01 Compose and Setup Ticket
- Stage 01 Loopback Publish Ticket
- Stage 02 вЂ” Accounts and Authentication
- Stage 02 Handoff 01-1
- Stage 02 Handoff 01-2
- Stage 02 Handoff 02-1
- Stage 02 Handoff 04-1
- Stage 02 Implementation Boundaries
- Stage 02 Requirement Manifest
- Stage 03 projects and passport brief
- Stage 03 implementation handoff
- Stage 03 implementation interfaces
- Stage 03 requirements manifest
- Project frontend
- T07 - Persist chat messages and provide REST history and sending
- T08 - Deliver chat events over authenticated WebSockets
- T09 - Upload, list, and download shared project documents
- T10 - Run the two-party archive, restore, and deletion lifecycle
- ChatPage.test.tsx
- Project-scoped executor and customer membership
- Build Progress Dashboard
- Autopilot Build Run Archive
- Server and Local UI State Separation
- Monorepo
- questionnaire/services.py
- QuestionnaireSchemaError
- start_submission
- ADR-001: Use a Monorepo
- ADR-002: Use a Modular Monolith for the Backend
- ADR-003: Use Feature-Sliced Design for the Frontend
- ADR-004: Use PostgreSQL as the Primary Database
- UserManager
- ADR-006: Use Per-Task AI Provider and Model Routing
- ADR-007: Shared Documents with Mutual-Consent Lifecycle
- ADR-008: Project-Scoped Roles and Shared Project State
- ADR-009-REVERSIBLE-PROJECT-ARCHIVING.md
- ADR-010-PASSPORT-OPTIMISTIC-CONCURRENCY.md
- ADR-011: Invitation expiry and rate limits
- ADR-012: Project State Entities and Transitions
- T11 - Validate browser origins for authenticated WebSockets
- ADR-014: Questionnaire Versioning and Passport Mapping
- manifest.md
- Изначальная задача

## God Nodes (most connected - your core abstractions)
1. `create_project()` - 91 edges
2. `CsrfSanitizingAPIView` - 77 edges
3. `RequireAuthenticatedUser` - 77 edges
4. `RequireCsrfForUnsafeRequests` - 77 edges
5. `ErrorEnvelopeSerializer` - 76 edges
6. `apiJson()` - 41 edges
7. `ProjectStateCollectionView` - 35 edges
8. `ProjectStateRecordView` - 34 edges
9. `ProjectStatePagination` - 31 edges
10. `ProjectStageCollectionView` - 31 edges

## Surprising Connections (you probably didn't know these)
- `restore_document()` --implements--> `D06: Restoration withdraws a one-party pending deletion request`  [INFERRED]
  backend/apps/documents/services.py → .autopilot/2026-11-12-stages-04-08-projectbridge/manifest.md
- `apply_questionnaire_mapping()` --implements--> `Versioned Questionnaire Mapping with Human Conflict Resolution`  [INFERRED]
  backend/apps/projects/services.py → docs/decisions/ADR-014-QUESTIONNAIRE-MAPPING-AND-VERSIONING.md
- `resolve_conflict()` --implements--> `Versioned Questionnaire Mapping with Human Conflict Resolution`  [INFERRED]
  backend/apps/questionnaire/services.py → docs/decisions/ADR-014-QUESTIONNAIRE-MAPPING-AND-VERSIONING.md
- `Private Executor AI Recommendations` --semantically_similar_to--> `Executor-Only AI Workspace`  [INFERRED] [semantically similar]
  projectbridge_mvp_demo.html → docs/security/ACCESS_CONTROL_AND_SECURITY.md
- `D06: Restoration withdraws a one-party pending deletion request` --references--> `ADR-013: Document Consent and Scheduled Deletion`  [INFERRED]
  .autopilot/2026-11-12-stages-04-08-projectbridge/manifest.md → docs/decisions/ADR-013-DOCUMENT-CONSENT-AND-DELETION.md

## Import Cycles
- None detected.

## Communities (190 total, 67 thin omitted)

### Community 0 - "questionnaire/api/views.py"
Cohesion: 0.20
Nodes (25): Meta, ProjectQuestionnaireResponseSerializer, QuestionnaireConflictResponseSerializer, QuestionnaireSubmissionResponseSerializer, RefreshQuestionnairePassportVersionSerializer, RequestQuestionnaireCorrectionSerializer, ResolveQuestionnaireConflictSerializer, SaveQuestionnaireAnswersSerializer (+17 more)

### Community 1 - "submit_submission"
Cohesion: 0.14
Nodes (37): get_passport_for_member(), lock_passport_for_update(), Apply an executor passport patch using an atomic version comparison., Lock and validate an executor's active-project passport for a transaction., update_passport(), _mapping_values_equal(), _passport_path_value(), _passport_value_for_mapping() (+29 more)

### Community 2 - "project_state/services.py"
Cohesion: 0.06
Nodes (87): get_message_for_evidence(), Resolve a message source while enforcing its project boundary., Evidence, EvidenceSourceType, ImmutableSnapshotQuerySet, Meta, OpenQuestion, OpenQuestionStatus (+79 more)

### Community 3 - "ErrorEnvelopeSerializer"
Cohesion: 0.08
Nodes (73): ErrorEnvelopeSerializer, DocumentLifecycleActionSerializer, DocumentLifecycleApprovalResponseSerializer, DocumentLifecycleRequestResponseSerializer, DocumentListResponseSerializer, DocumentResponseSerializer, DocumentUploadSerializer, EmptyLifecycleActionSerializer (+65 more)

### Community 4 - "create_project"
Cohesion: 0.06
Nodes (109): _archive_document_via_api(), _authenticated_client(), _create_active_document_pair(), django_db, fixture, parametrize, _request_deletion_via_api(), temporary_media_root() (+101 more)

### Community 5 - "ProjectStatePage.tsx"
Cohesion: 0.06
Nodes (59): CollectionResponse, createProjectStateRecord(), getAllPages(), getProjectStateAggregate(), getProjectStateCollection(), getProjectStateEvidenceOptions(), jsonBody(), projectPath() (+51 more)

### Community 6 - "CsrfSanitizingAPIView"
Cohesion: 0.11
Nodes (49): CsrfSanitizingAPIView, APIException, APIView, RequireAuthenticatedUser, RequireCsrfForUnsafeRequests, Unauthenticated, CredentialsSerializer, CsrfTokenSerializer (+41 more)

### Community 7 - "verification/views.py"
Cohesion: 0.09
Nodes (38): ConfirmVerificationRequestSerializer, ConfirmVerificationResponseSerializer, ResendVerificationRequestSerializer, ResendVerificationResponseSerializer, ConfirmVerificationView, APIView, extend_schema, ResendVerificationView (+30 more)

### Community 8 - "api/index.ts"
Cohesion: 0.12
Nodes (28): acceptInvitation(), previewInvitation(), ConfirmVerificationRequest, ConfirmVerificationResponse, Credentials, postJson(), ResendVerificationRequest, ResendVerificationResponse (+20 more)

### Community 9 - "documentsApi.ts"
Cohesion: 0.09
Nodes (33): CsrfToken, decideProjectDocumentLifecycle(), documentPath(), downloadProjectDocument(), getProjectDocuments(), postJson(), ProjectDocument, ProjectDocumentLifecycleAction (+25 more)

### Community 10 - "QuestionnairePage.tsx"
Cohesion: 0.12
Nodes (40): getProjectQuestionnaire(), getProjectQuestionnaireConflicts(), refreshQuestionnaireDraftPassportVersion(), requestQuestionnaireCorrection(), resolveQuestionnaireConflict(), saveQuestionnaireAnswers(), startQuestionnaireSubmission(), submitQuestionnaireSubmission() (+32 more)

### Community 11 - "Спецификация: ProjectBridge, этапы 04–08"
Cohesion: 0.08
Nodes (22): D06: Restoration withdraws a one-party pending deletion request, 10. Requirement coverage, 1. Задача, 2. Решение и пользовательские истории, 3. Решения, ограничения и продуктовые допущения, 4.1 Stage 04 — приглашения, 4.2 Stage 05 — анкета, 4.3 Stage 06 — Project State (+14 more)

### Community 12 - "devDependencies"
Cohesion: 0.04
Nodes (46): @biomejs/biome, dependencies, react, react-dom, react-router, @tanstack/react-query, devDependencies, @biomejs/biome (+38 more)

### Community 13 - "Stage 13: MVP Integration and Hardening"
Cohesion: 0.11
Nodes (46): ADR-013: Document Consent and Scheduled Deletion, Archive-First Mutual-Consent Deletion, Operational Backup Retention Boundary, Content-Free Deletion Tombstone, Thirty-Day Cancellation Window, Two-Party Document Consent, Document Storage and Lifecycle Contract, Document Lifecycle State Machine (+38 more)

### Community 14 - "chat/services.py"
Cohesion: 0.12
Nodes (32): atomic, Message, MessageType, Meta, get_messages_for_member(), ChatMessageConflictError, ChatMessageNotFoundError, ChatMessageRateLimitError (+24 more)

### Community 15 - "ProjectOverviewPage.tsx"
Cohesion: 0.09
Nodes (47): getProject(), getProjectMembers(), getProjectPassport(), getProjects(), shouldRetry(), useProject(), useProjectList(), useProjectMembers() (+39 more)

### Community 16 - "invitations/services.py"
Cohesion: 0.08
Nodes (56): AbstractUser, Migration, User, InvitationAcceptanceResponseSerializer, InvitationCreateSerializer, InvitationListResponseSerializer, InvitationPreviewRequestSerializer, InvitationPreviewResponseSerializer (+48 more)

### Community 17 - "chat/api/views.py"
Cohesion: 0.26
Nodes (11): MessageCreateSerializer, MessagePageResponseSerializer, MessageResponseSerializer, Meta, StrictChatSerializer, _message_page_link(), MessageConflict, ProjectMessagesView (+3 more)

### Community 18 - "projects/services.py"
Cohesion: 0.25
Nodes (22): Meta, Project, ProjectMember, ProjectMemberRole, ProjectMemberStatus, ProjectPassport, ProjectPreviousStatus, ProjectStatus (+14 more)

### Community 19 - "invitation/index.ts"
Cohesion: 0.21
Nodes (20): createProjectInvitation(), getProjectInvitations(), invitationsPath(), revokeProjectInvitation(), shouldRetry(), useProjectInvitations(), Invitation, InvitationAcceptance (+12 more)

### Community 20 - "compilerOptions"
Cohesion: 0.07
Nodes (27): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+19 more)

### Community 21 - "ChatPage.tsx"
Cohesion: 0.17
Nodes (16): ChatMessage, ChatMessageCreate, ChatMessagePage, createProjectMessage(), getProjectMessageCursor(), getProjectMessages(), projectPath(), shouldRetry() (+8 more)

### Community 22 - "Implementation interfaces and project rules"
Cohesion: 0.17
Nodes (11): 6. Границы и швы, Existing verification commands, From ticket T01 - invitation management, From ticket T02 - invitation preview and acceptance, From ticket T07 - persisted chat and REST history, From ticket T08 - authenticated WebSocket delivery, From ticket T09 - shared document storage and access, From ticket T10 - mutual-consent document lifecycle (+3 more)

### Community 23 - "biome.json"
Cohesion: 0.09
Nodes (21): files, ignoreUnknown, includes, formatter, enabled, indentStyle, indentWidth, jsxQuoteStyle (+13 more)

### Community 24 - "sync.py"
Cohesion: 0.18
Nodes (18): audit(), close_passed(), cmdline(), fail(), free_port(), http_ok(), is_ours(), main() (+10 more)

### Community 25 - "test_chat_api.py"
Cohesion: 0.23
Nodes (21): chat_api_context(), _client(), _messages_url(), django_db, fixture, test_both_project_roles_can_send_and_retry_idempotently(), test_chat_service_publishes_after_the_outer_transaction_commits(), test_chat_websocket_accepts_configured_frontend_origin() (+13 more)

### Community 26 - "test_auth.py"
Cohesion: 0.20
Nodes (15): clear_rate_limit_cache(), django_db, fixture, test_anonymous_browser_write_requires_bootstrapped_csrf_token(), test_anonymous_login_requires_bootstrapped_csrf_token(), test_authenticated_logout_requires_bootstrapped_csrf_token(), test_current_user_requires_and_returns_the_current_session(), test_login_creates_http_only_session_for_unverified_user() (+7 more)

### Community 27 - "ProjectChatConsumer"
Cohesion: 0.08
Nodes (15): D07: Validate project chat WebSocket origins, 4.4 Stage 07 — чат, _has_active_membership(), ProjectChatConsumer, AsyncJsonWebsocketConsumer, project_chat_group_name(), _publish_message_created(), Return the Channels group name for one project chat. (+7 more)

### Community 28 - "test_project_state_api.py"
Cohesion: 0.30
Nodes (15): _client(), _evidence_refs(), project_context(), django_db, fixture, parametrize, test_both_members_read_every_shared_collection_and_conflict_history(), test_completed_and_archived_projects_reject_project_state_mutations() (+7 more)

### Community 29 - "check_readiness"
Cohesion: 0.24
Nodes (11): api_view, check_readiness(), test_check_readiness_reports_available_dependencies(), test_check_readiness_reports_database_failure_without_exception_details(), test_check_readiness_reports_redis_failure_without_exception_details(), test_health_endpoint_returns_sanitized_success_response(), test_health_endpoint_returns_sanitized_unavailable_response(), health_check() (+3 more)

### Community 30 - "Versioned REST, WebSocket, and OpenAPI Contract"
Cohesion: 0.13
Nodes (15): Browser Session Authentication and CSRF, Deterministic Questionnaire Boundary, Consistent API Error Envelope, Stable Collection Pagination, Session Authentication and CSRF Contract, Versioned REST, WebSocket, and OpenAPI Contract, Domain-Owned Models and Services, Modular Monolith (+7 more)

### Community 31 - "project_state/api/views.py"
Cohesion: 0.24
Nodes (56): EvidenceOptionPageSerializer, EvidenceOptionResponseSerializer, EvidenceReferenceSerializer, EvidenceResponseSerializer, Meta, OpenQuestionCreateSerializer, OpenQuestionPageSerializer, OpenQuestionPatchSerializer (+48 more)

### Community 32 - "Stage 01 Specification"
Cohesion: 0.18
Nodes (11): ASGI and Channels Runtime, Celery Worker and Redis Task Runtime, Feature-Sliced Design, OpenAPI to TypeScript Type Generation, PostgreSQL pgvector Extension, Stage 01 Specification, Feature-Sliced Frontend Authentication Flow, Normalized Email Identity (+3 more)

### Community 33 - "api_exception_handler"
Cohesion: 0.35
Nodes (9): api_exception_handler(), csrf_failure(), _error_envelope(), _response_detail(), parametrize, test_api_exception_handler_hides_unexpected_exception_details(), test_api_exception_handler_maps_authentication_and_permission_errors(), test_api_exception_handler_wraps_validation_errors_in_stable_envelope() (+1 more)

### Community 34 - "test_questionnaire_submission_api.py"
Cohesion: 0.53
Nodes (10): _client(), _complete_answers(), _project_with_members(), django_db, _start_and_save(), test_conflict_queue_and_apply_decision_are_executor_only_and_audited(), test_customer_submits_completed_answers_and_cannot_edit_the_immutable_version(), test_executor_can_request_correction_and_questionnaire_read_preserves_history() (+2 more)

### Community 35 - "Plan - ProjectBridge stages 04-08"
Cohesion: 0.33
Nodes (5): Cross-cutting requirements, Plan - ProjectBridge stages 04-08, Stage boundaries, Ticket commit rule, Ticket order

### Community 36 - "test_questionnaire_api.py"
Cohesion: 0.61
Nodes (8): _active_project(), _auth_client(), django_db, test_customer_reads_schema_starts_and_resumes_a_draft(), test_draft_api_rejects_unknown_and_inactive_branch_answers_without_mutation(), test_questionnaire_api_enforces_customer_membership_and_project_scope(), test_questionnaire_draft_mutations_require_active_project(), test_schema_api_selects_each_project_type_and_exposes_the_full_branch_contract()

### Community 37 - "App.tsx"
Cohesion: 0.09
Nodes (15): App(), ProtectedAppPage(), rootElement, currentUserQueryKey, useCurrentUser(), User, HomePage(), errorResponse() (+7 more)

### Community 38 - "T01 - Issue and manage project invitations"
Cohesion: 0.33
Nodes (5): Acceptance criteria, From the brief, verbatim, Spec sections, T01 - Issue and manage project invitations, What must work

### Community 39 - "Technical Documentation Map"
Cohesion: 0.67
Nodes (3): OpenAPI Frontend Type Generation, Open and Resolved Decisions, Technical Documentation Map

### Community 41 - "run_production_process"
Cohesion: 0.43
Nodes (6): parametrize, run_production_process(), test_production_disables_debug_and_development_documentation_routes(), test_production_rejects_unsafe_secret_or_host_configuration(), test_production_uses_secure_browser_cookie_defaults(), CompletedProcess

### Community 42 - "Project-Scoped Roles and Shared Project State"
Cohesion: 0.33
Nodes (6): Email Verification as Product Access Gate, Executor Approval of AI Proposals, AI Contradiction Handling, Shared Documents with Mutual-Consent Lifecycle, Project-Scoped Roles and Shared Project State, Reversible Project Archiving

### Community 43 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 45 - "AI Router"
Cohesion: 0.40
Nodes (5): AI Model Profiles, AI Router, Embedding Compatibility, Provider Adapters and Capabilities, Retrieval-Augmented Generation Pipeline

### Community 46 - "T02 - Preview and accept project invitations"
Cohesion: 0.33
Nodes (5): Acceptance criteria, From the brief, verbatim, Spec sections, T02 - Preview and accept project invitations, What must work

### Community 48 - "Stage 00 Specification"
Cohesion: 0.67
Nodes (3): HTML Mockup as Product and Visual Reference, Monorepo Layout, Stage 00 Specification

### Community 49 - "Session-cookie authentication with CSRF protection"
Cohesion: 0.67
Nodes (3): Session authentication API, Session-cookie authentication with CSRF protection, Frontend authentication flows and route guards

### Community 50 - "Hashed single-use email verification tokens"
Cohesion: 0.67
Nodes (3): Email verification API, Hashed single-use email verification tokens, Verification email status copy

### Community 63 - "Invitation Expiry and Rate Limits"
Cohesion: 0.67
Nodes (3): Normalized Email as Account Identity, Email Verification Token Lifecycle, Invitation Expiry and Rate Limits

### Community 64 - "Relational Project Data Model"
Cohesion: 0.67
Nodes (3): Relational Project Data Model, Passport Optimistic Concurrency, Project State Entities and Transitions

### Community 65 - "Local Development and Operations Guide"
Cohesion: 0.67
Nodes (3): Docker Compose Local Runtime, Local Development and Operations Guide, Pinned Development Runtime

### Community 69 - "T03 - Build deterministic questionnaire schemas and drafts"
Cohesion: 0.33
Nodes (5): Acceptance criteria, From the brief, verbatim, Spec sections, T03 - Build deterministic questionnaire schemas and drafts, What must work

### Community 70 - "record_project_action"
Cohesion: 0.27
Nodes (8): ProjectAuditLog, record_project_action(), _validated_metadata(), add_customer_member_from_invitation(), Update executor-editable metadata and audit the changed field names., Join the invited customer and activate a draft project atomically., update_project_metadata(), ProjectMember

### Community 71 - "T05 - Create and edit Project State records"
Cohesion: 0.33
Nodes (5): Acceptance criteria, From the brief, verbatim, Spec sections, T05 - Create and edit Project State records, What must work

### Community 72 - "T06 - Expose shared Project State with evidence and conflict resolution"
Cohesion: 0.33
Nodes (5): Acceptance criteria, From the brief, verbatim, Spec sections, T06 - Expose shared Project State with evidence and conflict resolution, What must work

### Community 125 - "T07 - Persist chat messages and provide REST history and sending"
Cohesion: 0.33
Nodes (5): Acceptance criteria, From the brief, verbatim, Spec sections, T07 - Persist chat messages and provide REST history and sending, What must work

### Community 126 - "T08 - Deliver chat events over authenticated WebSockets"
Cohesion: 0.33
Nodes (5): Acceptance criteria, From the brief, verbatim, Spec sections, T08 - Deliver chat events over authenticated WebSockets, What must work

### Community 127 - "T09 - Upload, list, and download shared project documents"
Cohesion: 0.33
Nodes (5): Acceptance criteria, From the brief, verbatim, Spec sections, T09 - Upload, list, and download shared project documents, What must work

### Community 128 - "T10 - Run the two-party archive, restore, and deletion lifecycle"
Cohesion: 0.33
Nodes (5): Acceptance criteria, From the brief, verbatim, Spec sections, T10 - Run the two-party archive, restore, and deletion lifecycle, What must work

### Community 129 - "ChatPage.test.tsx"
Cohesion: 0.24
Nodes (5): chatFetch(), executor, jsonResponse(), message(), MockWebSocket

### Community 130 - "Project-scoped executor and customer membership"
Cohesion: 0.40
Nodes (5): Project-scoped executor and customer membership, Stage 03 projects and Project Passport specification, Versioned Project Passport with explicit mapping and conflict handling, Project domain and migrations, Passport and lifecycle API

### Community 169 - "questionnaire/services.py"
Cohesion: 0.17
Nodes (28): get_active_project_members(), QuestionnaireAnswerResponseSerializer, QuestionnaireQuestionSchemaSerializer, QuestionnaireSchemaResponseSerializer, Meta, QuestionnaireAnswer, QuestionnaireAnswerOrigin, QuestionnaireConflict (+20 more)

### Community 170 - "QuestionnaireSchemaError"
Cohesion: 0.18
Nodes (24): _decimal_value(), get_passport_prefill(), get_schema(), get_visible_questions(), _is_empty(), QuestionnaireSchemaError, The requested schema or answer payload does not meet its contract., Validate known, active answer keys and optionally require every visible field. (+16 more)

### Community 171 - "start_submission"
Cohesion: 0.31
Nodes (17): get_draft_for_project(), get_questionnaire_for_project(), Create or resume the one editable draft for an active customer project., Read the versioned questionnaire, active version, and immutable history., start_submission(), _active_project(), django_db, parametrize (+9 more)

### Community 172 - "ADR-001: Use a Monorepo"
Cohesion: 0.40
Nodes (4): ADR-001: Use a Monorepo, Consequences, Context, Decision

### Community 173 - "ADR-002: Use a Modular Monolith for the Backend"
Cohesion: 0.40
Nodes (4): ADR-002: Use a Modular Monolith for the Backend, Consequences, Context, Decision

### Community 174 - "ADR-003: Use Feature-Sliced Design for the Frontend"
Cohesion: 0.40
Nodes (4): ADR-003: Use Feature-Sliced Design for the Frontend, Consequences, Context, Decision

### Community 175 - "ADR-004: Use PostgreSQL as the Primary Database"
Cohesion: 0.40
Nodes (4): ADR-004: Use PostgreSQL as the Primary Database, Consequences, Context, Decision

### Community 176 - "UserManager"
Cohesion: 0.48
Nodes (3): UserManager, BaseUserManager, ValueError

### Community 177 - "ADR-006: Use Per-Task AI Provider and Model Routing"
Cohesion: 0.40
Nodes (4): ADR-006: Use Per-Task AI Provider and Model Routing, Consequences, Context, Decision

### Community 178 - "ADR-007: Shared Documents with Mutual-Consent Lifecycle"
Cohesion: 0.40
Nodes (4): ADR-007: Shared Documents with Mutual-Consent Lifecycle, Consequences, Context, Decision

### Community 179 - "ADR-008: Project-Scoped Roles and Shared Project State"
Cohesion: 0.40
Nodes (4): ADR-008: Project-Scoped Roles and Shared Project State, Consequences, Context, Decision

### Community 180 - "ADR-009-REVERSIBLE-PROJECT-ARCHIVING.md"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, Why

### Community 181 - "ADR-010-PASSPORT-OPTIMISTIC-CONCURRENCY.md"
Cohesion: 0.40
Nodes (4): Consequences, Context, Decision, Why

### Community 182 - "ADR-011: Invitation expiry and rate limits"
Cohesion: 0.40
Nodes (4): ADR-011: Invitation expiry and rate limits, Consequences, Context, Decision

### Community 183 - "ADR-012: Project State Entities and Transitions"
Cohesion: 0.40
Nodes (4): ADR-012: Project State Entities and Transitions, Consequences, Context, Decision

### Community 184 - "T11 - Validate browser origins for authenticated WebSockets"
Cohesion: 0.40
Nodes (4): Acceptance criteria, Finding, T11 - Validate browser origins for authenticated WebSockets, Verification

### Community 185 - "ADR-014: Questionnaire Versioning and Passport Mapping"
Cohesion: 0.40
Nodes (4): ADR-014: Questionnaire Versioning and Passport Mapping, Consequences, Context, Decision

### Community 186 - "manifest.md"
Cohesion: 0.50
Nodes (3): ASSUMPTIONS — принято за пользователя, Discovery during implementation, Phase 2 — self-briefing (full mode)

## Knowledge Gaps
- **301 isolated node(s):** `Meta`, `Migration`, `Meta`, `Meta`, `Migration` (+296 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **67 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_project()` connect `create_project` to `submit_submission`, `project_state/services.py`, `test_questionnaire_submission_api.py`, `test_questionnaire_api.py`, `CsrfSanitizingAPIView`, `record_project_action`, `start_submission`, `chat/services.py`, `projects/services.py`, `test_chat_api.py`, `test_project_state_api.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `ErrorEnvelopeSerializer` connect `ErrorEnvelopeSerializer` to `questionnaire/api/views.py`, `CsrfSanitizingAPIView`, `verification/views.py`, `invitations/services.py`, `chat/api/views.py`, `project_state/api/views.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `D06: Restoration withdraws a one-party pending deletion request` connect `Спецификация: ProjectBridge, этапы 04–08` to `ErrorEnvelopeSerializer`, `Stage 13: MVP Integration and Hardening`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 67 inferred relationships involving `CsrfSanitizingAPIView` (e.g. with `CsrfView` and `CurrentUserView`) actually correct?**
  _`CsrfSanitizingAPIView` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 67 inferred relationships involving `RequireAuthenticatedUser` (e.g. with `CsrfView` and `CurrentUserView`) actually correct?**
  _`RequireAuthenticatedUser` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 67 inferred relationships involving `RequireCsrfForUnsafeRequests` (e.g. with `CsrfView` and `CurrentUserView`) actually correct?**
  _`RequireCsrfForUnsafeRequests` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 67 inferred relationships involving `ErrorEnvelopeSerializer` (e.g. with `CsrfView` and `CurrentUserView`) actually correct?**
  _`ErrorEnvelopeSerializer` has 67 INFERRED edges - model-reasoned connections that need verification._