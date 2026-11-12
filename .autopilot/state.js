window.STATE =
{
  "slug": "stages-04-08-projectbridge",
  "dir": "2026-11-12-stages-04-08-projectbridge",
  "title": "ProjectBridge stages 04-08: invitations, questionnaire, project state, chat, documents",
  "mode": "full",
  "depth": "normal",
  "polish": null,
  "tier": "T3",
  "briefFile": "2026-11-12-brief.md",
  "memoryFile": "AGENTS.md",
  "skillDir": "C:/Users/McHomak/.agents/skills/autopilot",
  "startedAt": "2026-11-12T04:18:17+03:00",
  "updatedAt": "2026-11-12T18:23:58+03:00",
  "finishedAt": "2026-11-12T18:23:58+03:00",
  "stages": [
    {
      "id": "preflight",
      "status": "done",
      "startedAt": "2026-11-12T04:18:17+03:00",
      "finishedAt": "2026-11-12T04:20:24+03:00",
      "note": "New run prepared; Windows live dashboard server and browser panel unavailable, local snapshot retained."
    },
    {
      "id": "manifest",
      "status": "done",
      "startedAt": "2026-11-12T04:20:24+03:00",
      "finishedAt": "2026-11-12T04:28:02+03:00",
      "note": "102 requirements captured from the request and Stage 04-08 briefs."
    },
    {
      "id": "briefing",
      "status": "skipped",
      "startedAt": "2026-11-12T04:28:02+03:00",
      "finishedAt": "2026-11-12T04:33:53+03:00",
      "reason": "full mode self-briefing; user facts and external services are not invented",
      "note": "Product and lifecycle forks resolved as labelled ASSUMPTIONS in the manifest; no unresolved current-stage decision remains."
    },
    {
      "id": "spec",
      "status": "done",
      "startedAt": "2026-11-12T04:33:53+03:00",
      "finishedAt": "2026-11-12T05:00:43+03:00",
      "note": "G2 PASS; 1 finding fixed; 95 requirements specified, 7 deferred."
    },
    {
      "id": "plan",
      "status": "done",
      "startedAt": "2026-11-12T05:00:43+03:00",
      "note": "G3 PASS; 10 original T3 tickets in 10 waves; T11 added during final triage for WebSocket origin security.",
      "finishedAt": "2026-11-12T05:01:13+03:00"
    },
    {
      "id": "build",
      "status": "done",
      "startedAt": "2026-11-12T05:01:13+03:00",
      "note": "10 planned tickets and final T11 WebSocket origin hardening are implemented and committed; final full suites: backend 300 passed, frontend 72 passed.",
      "finishedAt": "2026-11-12T18:23:58+03:00"
    },
    {
      "id": "review",
      "status": "done",
      "startedAt": "2026-11-12T05:39:32+03:00",
      "note": "Manifest/spec, craft review, T11 re-review, and blind acceptance complete; no requirement drift. Live walkthrough did not exercise document restore/deletion cancellation.",
      "finishedAt": "2026-11-12T18:23:58+03:00"
    },
    {
      "id": "final",
      "status": "done",
      "startedAt": "2026-11-12T18:23:58+03:00",
      "finishedAt": "2026-11-12T18:23:58+03:00",
      "note": "Final report, memory, ADR, Graphify refresh, and run archive are closed; pushes are unavailable because no Git remote is configured."
    }
  ],
  "requirements": {
    "total": 102,
    "done": 95,
    "inTicket": 0,
    "inSpec": 0,
    "placeholder": 0,
    "deferred": 7,
    "dropped": 0
  },
  "tickets": [
    {
      "id": "T01",
      "title": "Issue and manage project invitations",
      "requirements": [
        "R01",
        "R02",
        "R05",
        "R10",
        "R12",
        "R14",
        "R15",
        "R20",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [
        "backend/apps/invitations/",
        "backend/apps/projects/",
        "frontend/src/entities/invitation/",
        "frontend/src/features/invitations/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 2,
      "handoffs": 0,
      "startedAt": "2026-11-12T05:02:51+03:00",
      "repairFindings": [
        "Full pytest collection reports import file mismatch: invitation test_api.py is imported in place of projects test_api.py; use a unique invitation test module name and preserve assertions.",
        "Full checks: Ruff format/check fail in five backend files; Biome format fails in InvitationManager.tsx and ProjectPages.test.tsx; Biome lint rejects aria-label on a span. Review blockers: paginate invitation list (R15), test active project creation (R10), move R21 completion to T02, and align the no-response-token security contract between T01/spec/docs."
      ],
      "finishedAt": "2026-11-12T06:03:25+03:00",
      "files": [
        "backend/apps/invitations/api/__init__.py",
        "backend/apps/invitations/api/serializers.py",
        "backend/apps/invitations/api/urls.py",
        "backend/apps/invitations/api/views.py",
        "backend/apps/invitations/migrations/0001_initial.py",
        "backend/apps/invitations/migrations/__init__.py",
        "backend/apps/invitations/models.py",
        "backend/apps/invitations/services.py",
        "backend/apps/invitations/tests/test_invitations_api.py",
        "backend/apps/projects/api/urls.py",
        "backend/apps/projects/selectors.py",
        "backend/apps/projects/services.py",
        "docs/OPEN_DECISIONS.md",
        "docs/api/API_CONTRACT.md",
        "docs/database/DATA_MODEL.md",
        "docs/decisions/ADR-011-INVITATION-EXPIRY-AND-RATE-LIMITS.md",
        "docs/security/ACCESS_CONTROL_AND_SECURITY.md",
        "frontend/src/app/styles.css",
        "frontend/src/entities/invitation/api/invitationApi.ts",
        "frontend/src/entities/invitation/index.ts",
        "frontend/src/entities/invitation/model/queries.ts",
        "frontend/src/entities/invitation/model/types.ts",
        "frontend/src/features/invitations/index.ts",
        "frontend/src/features/invitations/model/mutations.ts",
        "frontend/src/features/invitations/ui/InvitationManager.tsx",
        "frontend/src/pages/projects/ui/ProjectOverviewPage.tsx",
        "frontend/src/pages/projects/ui/ProjectPages.test.tsx",
        "frontend/src/shared/api/generated/schema.d.ts"
      ],
      "tests": {
        "passed": 132,
        "failed": 0
      },
      "commit": "f427226",
      "concerns": [
        "No regression assertion yet for 409 when a pending invitation already exists for the normalized project email."
      ]
    },
    {
      "id": "T02",
      "title": "Preview and accept project invitations",
      "requirements": [
        "R03",
        "R04",
        "R06",
        "R07",
        "R08",
        "R09",
        "R11",
        "R13",
        "R16",
        "R17",
        "R18",
        "R19",
        "R21",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [
        "T01"
      ],
      "wave": 2,
      "zone": [
        "backend/apps/invitations/",
        "backend/apps/projects/",
        "frontend/src/pages/invitations/",
        "frontend/src/app/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 1,
      "handoffs": 1,
      "startedAt": "2026-11-12T06:03:44+03:00",
      "finishedAt": "2026-11-12T07:22:18+03:00",
      "repairFindings": [
        "R19: acceptance frontend test only checked destination URL with project APIs mocked as 404; backend checked membership but not that the customer can read the accepted project."
      ],
      "tests": {
        "passed": 161,
        "failed": 0
      },
      "commit": "a011ffb",
      "files": [
        "backend/apps/invitations/api/serializers.py",
        "backend/apps/invitations/api/views.py",
        "backend/apps/invitations/api/public_urls.py",
        "backend/apps/invitations/services.py",
        "backend/apps/invitations/tests/test_invitations_api.py",
        "backend/apps/projects/services.py",
        "backend/apps/projects/tests/test_services.py",
        "backend/config/urls.py",
        "frontend/src/app/App.tsx",
        "frontend/src/entities/invitation/api/invitationApi.ts",
        "frontend/src/entities/invitation/index.ts",
        "frontend/src/entities/invitation/model/types.ts",
        "frontend/src/pages/invitations/index.ts",
        "frontend/src/pages/invitations/ui/InvitationPage.tsx",
        "frontend/src/pages/invitations/ui/InvitationPage.test.tsx",
        "frontend/src/shared/api/generated/schema.d.ts",
        "docs/api/API_CONTRACT.md",
        "docs/security/ACCESS_CONTROL_AND_SECURITY.md",
        "docs/decisions/ADR-011-INVITATION-EXPIRY-AND-RATE-LIMITS.md"
      ],
      "concerns": [
        "Dropped at final triage: the earlier enum-name warning did not recur in final drf-spectacular validation."
      ]
    },
    {
      "id": "T03",
      "title": "Build deterministic questionnaire schemas and drafts",
      "requirements": [
        "R22",
        "R23",
        "R24",
        "R25",
        "R33",
        "R34",
        "R35",
        "R39",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [
        "T02"
      ],
      "wave": 3,
      "zone": [
        "backend/apps/questionnaire/",
        "frontend/src/entities/questionnaire/",
        "frontend/src/features/questionnaire/",
        "frontend/src/pages/projects/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 2,
      "handoffs": 0,
      "startedAt": "2026-11-12T07:24:04+03:00",
      "finishedAt": "2026-11-12T08:26:47+03:00",
      "repairFindings": [
        "R24/spec 4.2: do not prefill non-mapping answers from additional_data.questionnaire; prefill only mapped passport fields.",
        "R34: list/object select values and malformed bracketed URLs must produce validation errors instead of 500s.",
        "R34: enforce exact YYYY-MM-DD format; Python date.fromisoformat accepts compact/week-date forms.",
        "Craft: malformed nested questionnaire prefill JSON must be ignored without raising AttributeError.",
        "R34: reject malformed HTTP(S) authorities (whitespace host and invalid port) as validation errors."
      ],
      "tests": {
        "passed": 206,
        "failed": 0
      },
      "files": [
        "backend/apps/projects/api/urls.py",
        "backend/config/urls.py",
        "backend/apps/questionnaire/models.py",
        "backend/apps/questionnaire/selectors.py",
        "backend/apps/questionnaire/services.py",
        "backend/apps/questionnaire/api/__init__.py",
        "backend/apps/questionnaire/api/project_urls.py",
        "backend/apps/questionnaire/api/serializers.py",
        "backend/apps/questionnaire/api/urls.py",
        "backend/apps/questionnaire/api/views.py",
        "backend/apps/questionnaire/schemas/__init__.py",
        "backend/apps/questionnaire/schemas/registry.py",
        "backend/apps/questionnaire/schemas/website.v1.json",
        "backend/apps/questionnaire/schemas/telegram_bot.v1.json",
        "backend/apps/questionnaire/schemas/automation.v1.json",
        "backend/apps/questionnaire/schemas/other.v1.json",
        "backend/apps/questionnaire/migrations/__init__.py",
        "backend/apps/questionnaire/migrations/0001_initial.py",
        "backend/apps/questionnaire/tests/test_questionnaire_api.py",
        "backend/apps/questionnaire/tests/test_questionnaire_schema.py",
        "backend/apps/questionnaire/tests/test_questionnaire_services.py",
        "frontend/src/app/App.tsx",
        "frontend/src/app/styles.css",
        "frontend/src/entities/questionnaire/api/questionnaireApi.ts",
        "frontend/src/entities/questionnaire/index.ts",
        "frontend/src/entities/questionnaire/model/queries.ts",
        "frontend/src/entities/questionnaire/model/types.ts",
        "frontend/src/features/questionnaire/index.ts",
        "frontend/src/features/questionnaire/model/mutations.ts",
        "frontend/src/pages/projects/index.ts",
        "frontend/src/pages/projects/ui/ProjectOverviewPage.tsx",
        "frontend/src/pages/projects/ui/ProjectPages.test.tsx",
        "frontend/src/pages/projects/ui/QuestionnairePage.tsx",
        "frontend/src/pages/projects/ui/QuestionnairePage.test.tsx",
        "frontend/src/shared/api/generated/schema.d.ts",
        "docs/OPEN_DECISIONS.md",
        "docs/api/API_CONTRACT.md",
        "docs/database/DATA_MODEL.md",
        "docs/product/MVP_SCOPE.md"
      ],
      "concerns": [
        "Dropped at final triage: the earlier enum-name warning did not recur in final drf-spectacular validation."
      ],
      "commit": "ea20ae1"
    },
    {
      "id": "T04",
      "title": "Submit questionnaires and resolve mappings, conflicts, and corrections",
      "requirements": [
        "R26",
        "R27",
        "R28",
        "R29",
        "R30",
        "R31",
        "R32",
        "R36",
        "R37",
        "R38",
        "R40",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [
        "T03"
      ],
      "wave": 4,
      "zone": [
        "backend/apps/questionnaire/",
        "backend/apps/projects/",
        "frontend/src/features/questionnaire/",
        "frontend/src/pages/projects/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 2,
      "handoffs": 0,
      "startedAt": "2026-11-12T08:28:01+03:00",
      "finishedAt": "2026-11-12T09:50:02+03:00",
      "repairFindings": [
        "R32: assert stored passport values for each project-type mapping and explicit has_integrations=false branch.",
        "After stale 409, provide a safe customer draft version refresh/retry path preserving answers and not mutating passport.",
        "Test that a customer cannot POST to resolve an executor conflict.",
        "R32: explicitly test budget_max mapped value persistence.",
        "Conflict keep resolution must lock and recheck passport version/snapshot before closing; stale changes must return safe conflict.",
        "Align stale 409 public code/detail with API contract and assert response."
      ],
      "tests": {
        "passed": 233,
        "failed": 0
      },
      "files": [
        "backend/apps/projects/services.py",
        "backend/apps/projects/tests/test_services.py",
        "backend/apps/questionnaire/api/project_urls.py",
        "backend/apps/questionnaire/api/serializers.py",
        "backend/apps/questionnaire/api/urls.py",
        "backend/apps/questionnaire/api/views.py",
        "backend/apps/questionnaire/models.py",
        "backend/apps/questionnaire/selectors.py",
        "backend/apps/questionnaire/services.py",
        "backend/apps/questionnaire/migrations/0002_questionnairesubmission_passport_version_and_more.py",
        "backend/apps/questionnaire/tests/test_questionnaire_submission_api.py",
        "backend/apps/questionnaire/tests/test_questionnaire_submission_services.py",
        "backend/config/settings/base.py",
        "docs/api/API_CONTRACT.md",
        "docs/database/DATA_MODEL.md",
        "frontend/src/app/styles.css",
        "frontend/src/entities/project/model/queries.ts",
        "frontend/src/entities/project/model/types.ts",
        "frontend/src/entities/questionnaire/api/questionnaireApi.ts",
        "frontend/src/entities/questionnaire/index.ts",
        "frontend/src/entities/questionnaire/model/queries.ts",
        "frontend/src/entities/questionnaire/model/types.ts",
        "frontend/src/features/questionnaire/index.ts",
        "frontend/src/features/questionnaire/model/mutations.ts",
        "frontend/src/pages/projects/ui/QuestionnairePage.tsx",
        "frontend/src/pages/projects/ui/QuestionnairePage.test.tsx",
        "frontend/src/shared/api/generated/schema.d.ts"
      ],
      "concerns": [
        "Unconfirmed passport-prefilled answers require explicit customer confirmation at submission, documented in the T04 product/API contract.",
        "Craft review notes the test covers stale-version resolution but not a same-version field mutation, which is outside the supported versioned project-owner write path."
      ],
      "commit": "e50dcb2"
    },
    {
      "id": "T05",
      "title": "Create and edit Project State records",
      "requirements": [
        "R48",
        "R50",
        "R52",
        "R54",
        "R57",
        "R58",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [
        "T04"
      ],
      "wave": 5,
      "zone": [
        "backend/apps/project_state/",
        "frontend/src/entities/project-state/",
        "frontend/src/features/project-state/",
        "frontend/src/pages/projects/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 2,
      "handoffs": 0,
      "startedAt": "2026-11-12T09:51:07+03:00",
      "finishedAt": "2026-11-12T11:16:37+03:00",
      "repairFindings": [
        "Frontend state/evidence lists must follow all paginated API pages, not stop at the first 100.",
        "Terminality prevents status transitions; content-only edits must match visible UI behavior, with terminal status locked.",
        "Add tests for requirement in_progress→rejected, task in_progress→cancelled, and an invalid transition.",
        "Assert update audit actor/target/changed field names or status transition, with no user content.",
        "Spec §4.3 makes resolved/dismissed conflicts immutable even though other terminal records allow content-only edits.",
        "Add allowed transition tests for requirement confirmed→rejected, requirement blocked→rejected, and task blocked→cancelled."
      ],
      "tests": {
        "passed": 300,
        "failed": 0
      },
      "files": [
        "backend/apps/project_state/models.py",
        "backend/apps/project_state/selectors.py",
        "backend/apps/project_state/services.py",
        "backend/apps/project_state/migrations/0001_initial.py",
        "backend/apps/project_state/migrations/__init__.py",
        "backend/apps/project_state/api/serializers.py",
        "backend/apps/project_state/api/urls.py",
        "backend/apps/project_state/api/views.py",
        "backend/apps/project_state/api/__init__.py",
        "backend/apps/project_state/tests/test_project_state_services.py",
        "backend/apps/project_state/tests/test_project_state_api.py",
        "backend/apps/questionnaire/selectors.py",
        "backend/apps/common/services.py",
        "backend/config/settings/base.py",
        "backend/config/urls.py",
        "frontend/src/entities/project-state/api/projectStateApi.ts",
        "frontend/src/entities/project-state/index.ts",
        "frontend/src/entities/project-state/model/queries.ts",
        "frontend/src/entities/project-state/model/types.ts",
        "frontend/src/features/project-state/index.ts",
        "frontend/src/features/project-state/model/mutations.ts",
        "frontend/src/pages/projects/ui/ProjectStatePage.tsx",
        "frontend/src/pages/projects/ui/ProjectStatePage.test.tsx",
        "frontend/src/app/App.tsx",
        "frontend/src/app/styles.css",
        "frontend/src/pages/projects/index.ts",
        "frontend/src/pages/projects/ui/ProjectOverviewPage.tsx",
        "frontend/src/shared/api/generated/schema.d.ts",
        "docs/OPEN_DECISIONS.md",
        "docs/api/API_CONTRACT.md",
        "docs/database/DATA_MODEL.md",
        "docs/decisions/ADR-012-PROJECT-STATE-TRANSITIONS.md"
      ],
      "concerns": [
        "Craft review noted the test table lacks a dedicated ProjectStage active→cancelled assertion; the service graph includes the transition and this was nonblocking."
      ],
      "commit": "0009b3f"
    },
    {
      "id": "T06",
      "title": "Expose shared Project State with evidence and conflict resolution",
      "requirements": [
        "R41",
        "R42",
        "R43",
        "R44",
        "R45",
        "R46",
        "R47",
        "R49",
        "R51",
        "R53",
        "R55",
        "R56",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [
        "T05"
      ],
      "wave": 6,
      "zone": [
        "backend/apps/project_state/",
        "backend/apps/questionnaire/",
        "frontend/src/entities/project-state/",
        "frontend/src/features/project-state/",
        "frontend/src/pages/projects/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 1,
      "handoffs": 0,
      "startedAt": "2026-11-12T11:18:00+03:00",
      "finishedAt": "2026-11-12T11:53:33+03:00",
      "repairFindings": [
        "R45: block positional as well as keyword bulk_create(update_conflicts=True) upserts to immutable Evidence snapshots and add regression for existing row."
      ],
      "tests": {
        "passed": 304,
        "failed": 0
      },
      "files": [
        "backend/apps/project_state/models.py",
        "backend/apps/project_state/tests/test_project_state_services.py",
        "backend/apps/project_state/tests/test_project_state_api.py",
        "frontend/src/pages/projects/ui/ProjectStatePage.test.tsx"
      ],
      "concerns": [
        "The keyword form of bulk_create(update_conflicts=True) shares the same bound guard as the tested positional form but has no separate regression assertion."
      ],
      "commit": "ce6c3b5"
    },
    {
      "id": "T07",
      "title": "Persist chat messages and provide REST history and sending",
      "requirements": [
        "R45",
        "R59",
        "R60",
        "R61",
        "R64",
        "R68",
        "R69",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [
        "T06"
      ],
      "wave": 7,
      "zone": [
        "backend/apps/chat/",
        "backend/apps/project_state/",
        "frontend/src/entities/chat/",
        "frontend/src/features/chat/",
        "frontend/src/pages/projects/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 2,
      "handoffs": 0,
      "startedAt": "2026-11-12T11:54:16+03:00",
      "repairFindings": [
        "Same-ID/same-content retry of a persisted message after project closure must return the prior message before applying active-only new-send checks.",
        "Add cursor pagination regression with equal created_at values to verify ID tie-breaker.",
        "Clarify REST limiter is reusable and T08 will wire WebSocket consumer; current docs must not claim consumer exists.",
        "API contract still claimed the limiter was already shared by REST and WebSocket; make T08 ownership explicit."
      ],
      "tests": {
        "passed": 326,
        "failed": 0
      },
      "finishedAt": "2026-11-12T14:10:36+03:00",
      "files": [
        "backend/apps/chat/__init__.py",
        "backend/apps/chat/apps.py",
        "backend/apps/chat/models.py",
        "backend/apps/chat/selectors.py",
        "backend/apps/chat/services.py",
        "backend/apps/chat/migrations/0001_initial.py",
        "backend/apps/chat/migrations/__init__.py",
        "backend/apps/chat/api/__init__.py",
        "backend/apps/chat/api/serializers.py",
        "backend/apps/chat/api/urls.py",
        "backend/apps/chat/api/views.py",
        "backend/apps/chat/tests/__init__.py",
        "backend/apps/chat/tests/test_chat_services.py",
        "backend/apps/chat/tests/test_chat_api.py",
        "backend/apps/project_state/api/serializers.py",
        "backend/apps/project_state/services.py",
        "backend/apps/project_state/tests/test_project_state_api.py",
        "backend/apps/project_state/tests/test_project_state_services.py",
        "backend/apps/projects/api/urls.py",
        "frontend/src/entities/chat/api/chatApi.ts",
        "frontend/src/entities/chat/api/chatApi.test.ts",
        "frontend/src/entities/chat/index.ts",
        "frontend/src/entities/chat/model/queries.ts",
        "frontend/src/entities/chat/model/types.ts",
        "frontend/src/features/chat/index.ts",
        "frontend/src/features/chat/model/mutations.ts",
        "frontend/src/pages/projects/ui/ChatPage.tsx",
        "frontend/src/pages/projects/ui/ChatPage.test.tsx",
        "frontend/src/app/App.tsx",
        "frontend/src/app/styles.css",
        "frontend/src/pages/projects/index.ts",
        "frontend/src/pages/projects/ui/ProjectOverviewPage.tsx",
        "frontend/src/shared/api/generated/schema.d.ts",
        "docs/OPEN_DECISIONS.md",
        "docs/api/API_CONTRACT.md",
        "docs/architecture/BACKEND_ARCHITECTURE.md",
        "docs/architecture/FRONTEND_ARCHITECTURE.md",
        "docs/database/DATA_MODEL.md"
      ],
      "concerns": [
        "The equal-timestamp cursor regression covers the older-page boundary; there is no separate equal-timestamp assertion for the newer/previous cursor direction."
      ],
      "commit": "7ac080a"
    },
    {
      "id": "T08",
      "title": "Deliver chat events over authenticated WebSockets",
      "requirements": [
        "R62",
        "R63",
        "R65",
        "R66",
        "R67",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [
        "T07"
      ],
      "wave": 8,
      "zone": [
        "backend/apps/chat/",
        "backend/config/asgi.py",
        "frontend/src/features/chat/",
        "frontend/src/pages/projects/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 0,
      "handoffs": 0,
      "startedAt": "2026-11-12T14:10:36+03:00",
      "tests": {
        "passed": 332,
        "failed": 0
      },
      "files": [
        "backend/apps/chat/services.py",
        "backend/apps/chat/consumers.py",
        "backend/apps/chat/routing.py",
        "backend/apps/chat/tests/test_chat_api.py",
        "backend/config/asgi.py",
        "frontend/src/pages/projects/ui/ChatPage.tsx",
        "frontend/src/pages/projects/ui/ChatPage.test.tsx",
        "docs/api/API_CONTRACT.md",
        "docs/architecture/BACKEND_ARCHITECTURE.md",
        "docs/OPEN_DECISIONS.md"
      ],
      "concerns": [
        "Resolved in T11 (87c6b74): chat WebSockets reject missing and foreign Origin values before session/member checks.",
        "Reported test gap: no direct revoked-member rejection assertion at WebSocket connect.",
        "Reported test gap: no explicit inbound-frame assertion for the event-only WebSocket protocol."
      ],
      "finishedAt": "2026-11-12T14:38:31+03:00",
      "commit": "a2a6880"
    },
    {
      "id": "T09",
      "title": "Upload, list, and download shared project documents",
      "requirements": [
        "R76",
        "R77",
        "R78",
        "R79",
        "R80",
        "R81",
        "R88",
        "R89",
        "R90",
        "R91",
        "R93",
        "R94",
        "R95",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [
        "T08"
      ],
      "wave": 9,
      "zone": [
        "backend/apps/documents/",
        "backend/apps/projects/api/urls.py",
        "backend/config/urls.py",
        "backend/config/settings/",
        "frontend/src/entities/documents/",
        "frontend/src/features/documents/",
        "frontend/src/pages/projects/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 1,
      "handoffs": 0,
      "startedAt": "2026-11-12T14:38:31+03:00",
      "repairFindings": [
        "R102i: the OpenAPI schema for GET /api/v1/documents/{document_id}/download/ must describe a binary file response, not application/json string."
      ],
      "tests": {
        "passed": 354,
        "failed": 0
      },
      "files": [
        "backend/apps/projects/api/urls.py",
        "backend/config/settings/base.py",
        "backend/config/urls.py",
        "backend/apps/documents/__init__.py",
        "backend/apps/documents/apps.py",
        "backend/apps/documents/models.py",
        "backend/apps/documents/selectors.py",
        "backend/apps/documents/services.py",
        "backend/apps/documents/api/__init__.py",
        "backend/apps/documents/api/document_urls.py",
        "backend/apps/documents/api/project_urls.py",
        "backend/apps/documents/api/serializers.py",
        "backend/apps/documents/api/views.py",
        "backend/apps/documents/migrations/__init__.py",
        "backend/apps/documents/migrations/0001_initial.py",
        "backend/apps/documents/migrations/0002_remove_document_document_file_size_positive.py",
        "backend/apps/documents/tests/__init__.py",
        "backend/apps/documents/tests/test_api.py",
        "docs/api/API_CONTRACT.md",
        "docs/database/DATA_MODEL.md",
        "docs/documents/DOCUMENT_LIFECYCLE.md",
        "docs/product/MVP_SCOPE.md",
        "docs/security/ACCESS_CONTROL_AND_SECURITY.md",
        "frontend/src/entities/documents/api/documentsApi.ts",
        "frontend/src/entities/documents/index.ts",
        "frontend/src/entities/documents/model/queries.ts",
        "frontend/src/entities/documents/model/types.ts",
        "frontend/src/features/documents/index.ts",
        "frontend/src/features/documents/model/mutations.ts",
        "frontend/src/pages/projects/ui/ProjectOverviewPage.tsx",
        "frontend/src/pages/projects/ui/ProjectDocumentsPanel.tsx",
        "frontend/src/pages/projects/ui/ProjectDocumentsPanel.css",
        "frontend/src/pages/projects/ui/ProjectDocumentsPanel.test.tsx",
        "frontend/src/shared/api/generated/schema.d.ts"
      ],
      "concerns": [
        "Production gate: malware scanning is not available in the local MVP.",
        "Resolved in T10 (ab19730): reset document pagination and invalidate lifecycle queries after success/failure; lost-response regression passes.",
        "Reported test gap: no explicit revoked-membership assertion for document list/detail/download selectors."
      ],
      "finishedAt": "2026-11-12T15:38:39+03:00",
      "commit": "9f45b90"
    },
    {
      "id": "T10",
      "title": "Run the two-party archive, restore, and deletion lifecycle",
      "requirements": [
        "R82",
        "R83",
        "R84",
        "R85",
        "R86",
        "R87",
        "R92",
        "R96",
        "R97",
        "R98",
        "R100i",
        "R101i",
        "R102i"
      ],
      "blockedBy": [
        "T09"
      ],
      "wave": 10,
      "zone": [
        "backend/apps/documents/",
        "backend/config/",
        "docker-compose.yml",
        "frontend/src/entities/documents/",
        "frontend/src/features/documents/",
        "frontend/src/pages/projects/",
        "frontend/src/shared/api/generated/schema.d.ts",
        "docs/api/",
        "docs/database/",
        "docs/documents/",
        "docs/security/",
        "docs/decisions/",
        "docs/OPEN_DECISIONS.md"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 1,
      "handoffs": 0,
      "startedAt": "2026-11-12T15:38:39+03:00",
      "tests": {
        "passed": 368,
        "failed": 0
      },
      "files": [
        "backend/apps/documents/api/document_urls.py",
        "backend/apps/documents/api/serializers.py",
        "backend/apps/documents/api/views.py",
        "backend/apps/documents/api/lifecycle_urls.py",
        "backend/apps/documents/selectors.py",
        "backend/apps/documents/services.py",
        "backend/apps/documents/tasks.py",
        "backend/apps/documents/tests/test_api.py",
        "backend/apps/documents/tests/test_tasks.py",
        "backend/config/settings/base.py",
        "backend/config/urls.py",
        "docker-compose.yml",
        "frontend/src/entities/documents/api/documentsApi.ts",
        "frontend/src/entities/documents/index.ts",
        "frontend/src/entities/documents/model/queries.ts",
        "frontend/src/entities/documents/model/types.ts",
        "frontend/src/features/documents/index.ts",
        "frontend/src/features/documents/model/mutations.ts",
        "frontend/src/pages/projects/ui/ProjectDocumentsPanel.tsx",
        "frontend/src/pages/projects/ui/ProjectDocumentsPanel.css",
        "frontend/src/pages/projects/ui/ProjectDocumentsPanel.test.tsx",
        "frontend/src/pages/projects/ui/ProjectOverviewPage.tsx",
        "frontend/src/shared/api/generated/schema.d.ts",
        "docs/OPEN_DECISIONS.md",
        "docs/api/API_CONTRACT.md",
        "docs/database/DATA_MODEL.md",
        "docs/documents/DOCUMENT_LIFECYCLE.md",
        "docs/security/ACCESS_CONTROL_AND_SECURITY.md",
        "docs/decisions/ADR-013-DOCUMENT-CONSENT-AND-DELETION.md"
      ],
      "concerns": [
        "No dedicated API regression assertion yet that lifecycle request creation and second-party approval both return 409 after project completion."
      ],
      "finishedAt": "2026-11-12T17:27:54+03:00",
      "commit": "ab19730",
      "repairFindings": [
        "R101i: refresh document queries after success or failure, reset pagination, and cover a committed write with a lost response. D06: restore cancels a pending one-party deletion request and audits the withdrawal."
      ]
    },
    {
      "id": "T11",
      "title": "Validate browser origins for authenticated WebSockets",
      "requirements": [
        "R65"
      ],
      "blockedBy": [
        "T08"
      ],
      "wave": 11,
      "zone": [
        "backend/apps/chat/routing.py",
        "backend/config/asgi.py",
        "backend/apps/chat/tests/test_chat_api.py",
        "backend/apps/health/tests/test_asgi.py",
        "docs/security/",
        "docs/decisions/"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 1,
      "handoffs": 0,
      "finishedAt": "2026-11-12T18:23:58+03:00",
      "repairFindings": [
        "The first full run found the global origin wrapper rejected originless health WebSockets; validation was moved to the chat route only."
      ],
      "tests": {
        "passed": 15,
        "failed": 0
      },
      "files": [
        "backend/apps/chat/routing.py",
        "backend/apps/chat/tests/test_chat_api.py",
        "backend/config/asgi.py",
        "docs/decisions/ADR-005-REST-WEBSOCKET-OPENAPI.md",
        "docs/security/ACCESS_CONTROL_AND_SECURITY.md",
        ".autopilot/2026-11-12-stages-04-08-projectbridge/manifest.md",
        ".autopilot/2026-11-12-stages-04-08-projectbridge/spec.md",
        ".autopilot/2026-11-12-stages-04-08-projectbridge/tickets/T11.md"
      ],
      "concerns": []
    }
  ],
  "singlePass": null,
  "tests": {
    "passed": 372,
    "failed": 0
  },
  "debt": {
    "placeholders": [],
    "assumptions": [
      "Assumption 01: project invitations expire after 7 days; acceptance requires the matching verified normalized email.",
      "Assumption 02: invitation preview 30/hour/IP, acceptance 10/hour/user, creation 20/hour/executor; Redis-backed limits.",
      "Assumption 03: four product-authored version-1 questionnaires with required common fields and deterministic project-type branches.",
      "Assumption 04: immutable questionnaire schema versions; correction submissions keep the original version.",
      "Assumption 05: explicit passport mapping; optional empty answers do not clear fields; conflicting values enter executor review without overwrite.",
      "Assumption 06: corrections create a superseding draft and preserve submitted history.",
      "Assumption 07: executor-only questionnaire conflict decisions are keep-passport or apply-answer via versioned passport service.",
      "Assumption 08: Project State enums/transitions are fixed and terminal as documented in the manifest.",
      "Assumption 09: evidence sources in this scope are same-project messages and questionnaire answers; provenance is immutable and audited.",
      "Assumption 10: chat history page size 50/max 100, message length 10,000, active-only sending, 60/minute/user.",
      "Assumption 11: document maximum is 20*1024*1024 bytes; archive-first deletion and 30-day cancellation starts after second approval.",
      "Assumption 12: text extraction/OCR/embeddings remain Stage 09; malware scanning remains a production gate.",
      "Assumption 13: reuse protected app routes, backend authorization, REST source-of-truth, and existing UI conventions.",
      "Assumption 14: raw invitation token is email-only; create API response excludes it to minimize exposure."
    ],
    "emptyEnv": []
  },
  "additions": [],
  "coverage": {
    "found": 1,
    "fixed": 1,
    "deferred": 0
  },
  "concerns": [
    "Reported test gap: no dedicated assertion for 409 when a pending invitation already exists for the normalized project email.",
    "Reported test gap: no same-version field-mutation test for the unsupported direct mutation path; passport writes go through the versioned owner service.",
    "Reported test gap: no dedicated ProjectStage active-to-cancelled assertion.",
    "Reported test gap: keyword-form bulk_create(update_conflicts=True) is not separately tested; the shared guard is exercised by the positional form.",
    "Reported test gap: equal-timestamp cursor coverage does not separately assert the newer/previous-page direction.",
    "Reported test gaps: no direct revoked-member WebSocket-connect assertion or inbound-frame assertion for the event-only protocol.",
    "Reported test gap: no explicit revoked-membership assertions for document list/detail/download selectors.",
    "Reported test gap: lifecycle request creation and second-party approval lack a dedicated 409-after-project-completion API assertion.",
    "Blind walkthrough did not manually exercise restore and permanent-deletion cancellation; backend lifecycle tests cover restore/cancel and frontend tests cover deletion cancellation.",
    "Production release gate: uploaded documents are not malware-scanned in this local MVP."
  ],
  "reviewers": {
    "manifestSpec": "stage04_ms_reviewer",
    "craft": "stage04_craft_reviewer"
  },
  "blind": {
    "matched": 4,
    "checked": 5,
    "mismatches": [
      "Stage 08 live walkthrough verified shared upload/download and both-party archive, but did not manually exercise restore or permanent-deletion cancellation. Automated backend lifecycle tests passed; text status remaining Queued is expected because extraction is Stage 09."
    ],
    "verdict": "findings",
    "commands": [
      "docker compose up --build -d ? exit 0; containers started.",
      "docker compose exec backend python manage.py migrate ? no migrations to apply.",
      "Invoke-WebRequest http://127.0.0.1:5173 ? HTTP 200.",
      "Invoke-WebRequest http://127.0.0.1:8001/api/v1/health/ ? HTTP 200; database and Redis healthy."
    ],
    "runtime": "Invitation acceptance, questionnaire submission and passport mapping, customer read-only Project State, chat send, document upload/download, and two-party archive were observed in the browser. Document remained Queued as designed for Stage 09."
  },
  "triage": {
    "fixed": [
      "T08 missing WebSocket Origin validation; fixed in T11 commit 87c6b74.",
      "T09 document page reset/query invalidation; fixed in T10 commit ab19730."
    ],
    "reported": [
      "Test-coverage gaps retained in concerns.",
      "Malware scanning requires a production scanner decision."
    ],
    "dropped": [
      "Earlier OpenAPI invitation enum-name warning did not recur in final schema validation."
    ]
  }
};
