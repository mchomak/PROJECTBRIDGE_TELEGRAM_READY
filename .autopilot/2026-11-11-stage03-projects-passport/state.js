window.STATE =
{
    "slug": "stage03-projects-passport",
    "dir": "2026-11-11-stage03-projects-passport",
    "title": "Stage 03 — Projects and Project Passport",
    "mode": "full",
    "depth": "normal",
    "polish": null,
    "tier": "T2",
    "briefFile": "2026-11-11-brief.md",
    "memoryFile": "AGENTS.md",
    "skillDir": "C:/Users/McHomak/.agents/skills/autopilot",
    "startedAt": "2026-11-11T21:56:46+03:00",
    "updatedAt": "2026-11-12T04:09:34+03:00",
    "finishedAt": "2026-11-12T04:09:34+03:00",
    "stages": [
        {
            "id": "preflight",
            "status": "done",
            "startedAt": "2026-11-11T21:56:46+03:00",
            "finishedAt": "2026-11-11T21:58:06+03:00"
        },
        {
            "id": "manifest",
            "status": "done",
            "startedAt": "2026-11-11T21:58:06+03:00",
            "finishedAt": "2026-11-11T22:01:48+03:00"
        },
        {
            "id": "briefing",
            "status": "done",
            "startedAt": "2026-11-11T22:01:48+03:00",
            "finishedAt": "2026-11-11T22:38:36+03:00",
            "note": "Owner-approved lifecycle decisions documented; G1 passed with requirements ready for spec mapping."
        },
        {
            "id": "spec",
            "status": "done",
            "startedAt": "2026-11-11T22:38:36+03:00",
            "finishedAt": "2026-11-11T23:11:20+03:00",
            "note": "G2 passed: no missing or partial requirements; refinements attached to parents."
        },
        {
            "id": "plan",
            "status": "done",
            "startedAt": "2026-11-11T23:11:20+03:00",
            "finishedAt": "2026-11-11T23:16:27+03:00",
            "note": "4 tasks, tier T2; sequential waves follow domain, API, and UI dependencies."
        },
        {
            "id": "build",
            "status": "done",
            "startedAt": "2026-11-11T23:16:27+03:00",
            "note": "All 4 Stage 03 tickets are committed; 2 non-blocking frontend Craft concerns remain for final triage.",
            "finishedAt": "2026-11-12T03:43:24+03:00"
        },
        {
            "id": "review",
            "status": "done",
            "startedAt": "2026-11-11T23:42:05+03:00",
            "note": "All tickets passed independent reviews; blocking API schema and stale-refetch findings were repaired and re-reviewed.",
            "finishedAt": "2026-11-12T03:42:26+03:00"
        },
        {
            "id": "final",
            "status": "done",
            "startedAt": "2026-11-12T03:45:17+03:00",
            "note": "Blind acceptance and final verification are complete; no manifest disagreements.",
            "finishedAt": "2026-11-12T04:09:34+03:00"
        }
    ],
    "requirements": {
        "total": 73,
        "done": 63,
        "inTicket": 0,
        "inSpec": 0,
        "placeholder": 0,
        "deferred": 10,
        "dropped": 0
    },
    "tickets": [
        {
            "id": "01",
            "title": "Модели проектов и транзакционный сервис создания",
            "requirements": [
                "R04",
                "R06",
                "R07",
                "R32",
                "R38",
                "R44",
                "R46",
                "R47",
                "G01",
                "G22",
                "G23"
            ],
            "blockedBy": [],
            "wave": 1,
            "zone": [
                "backend/apps/projects/",
                "backend/apps/common/"
            ],
            "status": "done",
            "startedAt": "2026-11-11T23:19:57+03:00",
            "finishedAt": "2026-11-12T00:00:43+03:00",
            "files": [
                "backend/apps/projects/models.py",
                "backend/apps/projects/services.py",
                "backend/apps/projects/migrations/0001_initial.py",
                "backend/apps/projects/migrations/0002_project_constraints.py",
                "backend/apps/projects/tests/test_services.py",
                "backend/apps/common/models.py",
                "backend/apps/common/services.py",
                "backend/apps/common/migrations/0002_project_audit_log.py"
            ],
            "tests": {
                "passed": 54,
                "failed": 0
            },
            "commit": "d2728fe",
            "concerns": [
                "Non-blocking Craft note: no dedicated regression test asserts safety against arbitrary unsafe audit metadata."
            ],
            "retries": 0,
            "repairs": 0,
            "handoffs": 0
        },
        {
            "id": "02",
            "title": "Project CRUD API и проверки доступа",
            "requirements": [
                "R05",
                "R08",
                "R09",
                "R10",
                "R11",
                "R12",
                "R34",
                "R37",
                "R39",
                "R40",
                "R41",
                "R44",
                "R45",
                "G14",
                "G15"
            ],
            "blockedBy": [
                "01"
            ],
            "wave": 2,
            "zone": [
                "backend/apps/projects/",
                "backend/apps/projects/api/",
                "backend/config/"
            ],
            "status": "done",
            "startedAt": "2026-11-12T00:01:10+03:00",
            "retries": 1,
            "handoffs": 1,
            "files": [
                "backend/config/urls.py",
                "backend/apps/projects/api/__init__.py",
                "backend/apps/projects/api/views.py",
                "backend/apps/projects/api/serializers.py",
                "backend/apps/projects/api/urls.py",
                "backend/apps/projects/selectors.py",
                "backend/apps/projects/services.py",
                "backend/apps/projects/tests/test_api.py",
                ".autopilot/2026-11-11-stage03-projects-passport/handoff-02-1.md"
            ],
            "tests": {
                "passed": 72,
                "failed": 0
            },
            "repairs": 1,
            "concerns": [
                "Dropped at final triage: the reported QueryDict unknown-field failure did not reproduce; Mapping guards and URL-encoded POST/PATCH regression tests remain."
            ],
            "finishedAt": "2026-11-12T01:41:19+03:00",
            "commit": "b2961ec"
        },
        {
            "id": "03",
            "title": "Passport и project lifecycle API",
            "requirements": [
                "R13",
                "R14",
                "R15",
                "R16",
                "R17",
                "R33",
                "R34",
                "R36",
                "R41",
                "R42",
                "R43",
                "R45",
                "R46",
                "R47",
                "G01",
                "G03",
                "G04",
                "G05",
                "G06",
                "G07",
                "G08",
                "G09",
                "G15",
                "G16",
                "G17",
                "G18",
                "G19",
                "G20",
                "G21",
                "G22",
                "G23",
                "A01"
            ],
            "blockedBy": [
                "02"
            ],
            "wave": 3,
            "zone": [
                "backend/apps/projects/",
                "backend/apps/projects/api/",
                "backend/config/"
            ],
            "status": "done",
            "retries": 0,
            "repairs": 1,
            "handoffs": 0,
            "startedAt": "2026-11-12T01:41:58+03:00",
            "tests": {
                "passed": 91,
                "failed": 0
            },
            "files": [
                "backend/apps/projects/services.py",
                "backend/apps/projects/selectors.py",
                "backend/apps/projects/api/serializers.py",
                "backend/apps/projects/api/views.py",
                "backend/apps/projects/api/urls.py",
                "backend/apps/projects/tests/test_services.py",
                "backend/apps/projects/tests/test_api.py"
            ],
            "concerns": [],
            "finishedAt": "2026-11-12T02:31:25+03:00",
            "commit": "5912cd1",
            "repairCommit": "87f39bf"
        },
        {
            "id": "04",
            "title": "Project list, passport и overview в приложении",
            "requirements": [
                "R01",
                "R18",
                "R19",
                "R20",
                "R21",
                "R22",
                "R23",
                "R24",
                "R25",
                "R26",
                "R35",
                "R36",
                "R42",
                "R43",
                "R47",
                "R48",
                "G01",
                "G03",
                "G04",
                "G05",
                "G06",
                "G08",
                "G09",
                "G14",
                "G15",
                "G16",
                "G17",
                "G20",
                "G21",
                "G22",
                "G23",
                "G25"
            ],
            "blockedBy": [
                "03"
            ],
            "wave": 4,
            "zone": [
                "frontend/src/"
            ],
            "status": "done",
            "retries": 0,
            "repairs": 1,
            "handoffs": 0,
            "startedAt": "2026-11-12T02:16:30+03:00",
            "tests": {
                "passed": 29,
                "failed": 0
            },
            "files": [
                "frontend/src/app/App.test.tsx",
                "frontend/src/app/App.tsx",
                "frontend/src/app/styles.css",
                "frontend/src/entities/project/api/projectApi.ts",
                "frontend/src/entities/project/index.ts",
                "frontend/src/entities/project/model/queries.ts",
                "frontend/src/entities/project/model/types.ts",
                "frontend/src/features/projects/index.ts",
                "frontend/src/features/projects/model/mutations.ts",
                "frontend/src/pages/projects/index.ts",
                "frontend/src/pages/projects/ui/ProjectCreatePage.tsx",
                "frontend/src/pages/projects/ui/ProjectListPage.tsx",
                "frontend/src/pages/projects/ui/ProjectOverviewPage.tsx",
                "frontend/src/pages/projects/ui/ProjectPages.test.tsx",
                "frontend/src/shared/api/generated/schema.d.ts",
                "frontend/src/widgets/workspace-shell/index.ts",
                "frontend/src/widgets/workspace-shell/ui/WorkspaceShell.tsx"
            ],
            "concerns": [
                "Non-blocking Craft note: passport field errors lack aria-invalid/aria-describedby associations.",
                "Non-blocking Craft note: no page-level test exercises executor metadata PATCH."
            ],
            "finishedAt": "2026-11-12T03:43:24+03:00",
            "commit": "36ae9d2"
        }
    ],
    "singlePass": null,
    "tests": {
        "passed": 120,
        "failed": 0
    },
    "debt": {
        "placeholders": [],
        "assumptions": [
            "R06.1: membership status values active/left/revoked and one row per (project, user), following DATA_MODEL.md.",
            "R07/R15.1: passport text defaults to empty strings, JSONB to {}, nullable fields to null; no new requiredness.",
            "R08.1: project list uses page size 20, maximum 100, order updated_at DESC then id ASC, local to this endpoint.",
            "R09.1: project name is trimmed and limited to 200 characters.",
            "R12.1: member summaries show ID, role, joined time, first and last name; no email.",
            "R13.1: completed_at marks the latest completion, remains on reopen, and updates at the next completion.",
            "R15.1: currency accepts three ASCII letters and normalizes to uppercase, without a fixed currency catalogue.",
            "Ticket 01: passport decimal precision is 30 digits / 10 places because the model baseline does not specify precision."
        ],
        "emptyEnv": []
    },
    "additions": [
        "A01 → R17 — project security-relevant mutations are auditable per ACCESS_CONTROL_AND_SECURITY.md"
    ],
    "coverage": {
        "found": 9,
        "fixed": 9,
        "deferred": 0,
        "notes": [
            "Added G24 for the documentation prerequisite and corrected its sequence without claiming prior completion.",
            "Deferred G02 and removed the Stage 03 customer-membership/acceptance workflow; Stage 04 owns it.",
            "Attached the ProjectAuditLog addition to R17 as A01 per the security baseline.",
            "Attached completion timestamp semantics to R13.1 and membership constraints/details to R06.1.",
            "Attached project-list defaults to R08.1, project-name validation to R09.1, member summary to R12.1, passport defaults/currency to R15.1, and archive timestamp consistency to R14.1.",
            "Added G25 to preserve existing code and prior run artifacts unless a Stage 03 change is necessary."
        ]
    },
    "concerns": [
        "Ticket 01: no dedicated regression test asserts safety against arbitrary unsafe audit metadata; reviewer marked non-blocking.",
        "Ticket 04: passport field errors lack aria-invalid/aria-describedby associations; reviewer marked non-blocking.",
        "Ticket 04: no page-level test exercises executor metadata PATCH; reviewer marked non-blocking.",
        "Dropped at final triage: QueryDict unknown-field failure was not reproduced; URL-encoded POST/PATCH regression coverage remains."
    ],
    "reviewers": {
        "manifestSpec": "stage03_manifest_spec_reviewer",
        "craft": "stage03_craft_reviewer"
    },
    "blind": {
        "matched": 63,
        "checked": 73,
        "mismatches": [],
        "notes": [
            "Blind review found the Stage 03 project, membership, passport, lifecycle, API, permission, and UI slice implemented and covered by tests.",
            "Invitation acceptance/customer membership and chat, document, Project State, and questionnaire read-only policies are partial/deferred to their owning stages; the checker found no disagreement with the scoped brief.",
            "The app launched; health returned 200 and anonymous project access returned 401. The authenticated browser route redirected to login because no verified local test account was available; no persistent user/project data was created.",
            "All project/common migrations were applied to the local database."
        ]
    }
};
