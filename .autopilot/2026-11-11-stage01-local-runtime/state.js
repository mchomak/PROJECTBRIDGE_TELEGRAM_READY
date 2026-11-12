window.STATE =
{
  "slug": "stage01-local-runtime",
  "dir": "2026-11-11-stage01-local-runtime",
  "title": "ProjectBridge Stage 01 — Application Skeleton and Local Runtime",
  "mode": "full",
  "depth": "normal",
  "polish": null,
  "tier": "T2",
  "briefFile": "2026-11-11-brief.md",
  "memoryFile": "AGENTS.md",
  "skillDir": "C:/Users/McHomak/.agents/skills/autopilot",
  "startedAt": "2026-11-11T03:33:08+03:00",
  "updatedAt": "2026-11-11T12:49:13+03:00",
  "finishedAt": "2026-11-11T12:49:13+03:00",
  "stages": [
    {
      "status": "done",
      "startedAt": "2026-11-11T03:33:08+03:00",
      "id": "preflight",
      "finishedAt": "2026-11-11T03:33:51+03:00"
    },
    {
      "id": "manifest",
      "status": "done",
      "startedAt": "2026-11-11T03:33:51+03:00",
      "finishedAt": "2026-11-11T03:42:44+03:00",
      "note": "54 requirements recorded; G1 closed with no open decisions."
    },
    {
      "id": "briefing",
      "status": "skipped",
      "reason": "Full mode self-briefing; no unresolved product questions.",
      "note": "No blocking or user-only decisions remain."
    },
    {
      "id": "spec",
      "status": "done",
      "startedAt": "2026-11-11T03:42:44+03:00",
      "finishedAt": "2026-11-11T04:00:54+03:00",
      "note": "G2 passed; spec aligns to project API path contract."
    },
    {
      "id": "plan",
      "status": "done",
      "startedAt": "2026-11-11T04:00:54+03:00",
      "note": "T2; 3 tickets in 3 sequential waves.",
      "finishedAt": "2026-11-11T04:03:31+03:00"
    },
    {
      "id": "build",
      "status": "done",
      "startedAt": "2026-11-11T04:03:31+03:00",
      "note": "All four tickets implemented and committed; backend and frontend runtime remain healthy.",
      "finishedAt": "2026-11-11T12:37:42+03:00"
    },
    {
      "id": "review",
      "status": "done",
      "startedAt": "2026-11-11T05:04:27+03:00",
      "note": "Manifest, Spec, and Craft reviews passed for Tickets 01?04; no blocking findings remain.",
      "finishedAt": "2026-11-11T12:37:42+03:00"
    },
    {
      "id": "final",
      "status": "done",
      "startedAt": "2026-11-11T12:37:42+03:00",
      "finishedAt": "2026-11-11T12:49:13+03:00",
      "note": "G4 blind acceptance passed against the original brief; memory and ADRs recorded."
    }
  ],
  "requirements": {
    "done": 50,
    "inTicket": 0,
    "inSpec": 0,
    "total": 54,
    "deferred": 4,
    "dropped": 0,
    "placeholder": 0
  },
  "tickets": [
    {
      "id": "01",
      "title": "Django runtime and API skeleton",
      "requirements": [
        "R08",
        "R09",
        "R10",
        "R11",
        "R12",
        "R13",
        "R14",
        "R15",
        "R16",
        "R33",
        "R34",
        "R35",
        "R36",
        "R37",
        "R42",
        "R43",
        "R44",
        "R45",
        "R46",
        "R47",
        "R50",
        "R53"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [
        "backend/"
      ],
      "status": "done",
      "retries": 2,
      "repairs": 0,
      "repairFindings": [],
      "handoffs": 1,
      "files": [
        "backend/apps/__init__.py",
        "backend/apps/accounts/__init__.py",
        "backend/apps/accounts/apps.py",
        "backend/apps/ai_assistant/__init__.py",
        "backend/apps/ai_assistant/apps.py",
        "backend/apps/chat/__init__.py",
        "backend/apps/chat/apps.py",
        "backend/apps/common/__init__.py",
        "backend/apps/common/apps.py",
        "backend/apps/common/migrations/0001_enable_pgvector.py",
        "backend/apps/common/migrations/__init__.py",
        "backend/apps/common/tasks.py",
        "backend/apps/common/tests/test_migrations.py",
        "backend/apps/common/tests/test_tasks.py",
        "backend/apps/documents/__init__.py",
        "backend/apps/documents/apps.py",
        "backend/apps/health/__init__.py",
        "backend/apps/health/apps.py",
        "backend/apps/health/checks.py",
        "backend/apps/health/consumers.py",
        "backend/apps/health/routing.py",
        "backend/apps/health/tests/test_asgi.py",
        "backend/apps/health/tests/test_readiness.py",
        "backend/apps/health/tests/test_schema.py",
        "backend/apps/health/urls.py",
        "backend/apps/health/views.py",
        "backend/apps/invitations/__init__.py",
        "backend/apps/invitations/apps.py",
        "backend/apps/project_state/__init__.py",
        "backend/apps/project_state/apps.py",
        "backend/apps/projects/__init__.py",
        "backend/apps/projects/apps.py",
        "backend/apps/questionnaire/__init__.py",
        "backend/apps/questionnaire/apps.py",
        "backend/apps/specifications/__init__.py",
        "backend/apps/specifications/apps.py",
        "backend/config/__init__.py",
        "backend/config/asgi.py",
        "backend/config/celery_app.py",
        "backend/config/settings/__init__.py",
        "backend/config/settings/base.py",
        "backend/config/settings/local.py",
        "backend/config/settings/production.py",
        "backend/config/settings/test.py",
        "backend/config/tests/test_production_settings.py",
        "backend/config/urls.py",
        "backend/manage.py",
        "backend/pyproject.toml",
        "backend/requirements.txt"
      ],
      "tests": {
        "passed": 13,
        "failed": 0
      },
      "commit": "b0adfbc",
      "concerns": [],
      "startedAt": "2026-11-11T04:03:49+03:00",
      "finishedAt": "2026-11-11T05:09:08+03:00"
    },
    {
      "id": "02",
      "title": "React/Vite shell and API contract boundary",
      "requirements": [
        "R17",
        "R18",
        "R19",
        "R20",
        "R21",
        "R22",
        "R23",
        "R33",
        "R38",
        "R41",
        "R48",
        "R50",
        "R53"
      ],
      "blockedBy": [
        "01"
      ],
      "wave": 2,
      "zone": [
        "frontend/"
      ],
      "status": "done",
      "retries": 2,
      "repairs": 1,
      "repairFindings": [
        "Coordinator format:check failed after build because generated dist assets were included in Biome; repaired by excluding dist and verified before and after build."
      ],
      "handoffs": 0,
      "files": [
        "frontend/biome.json",
        "frontend/index.html",
        "frontend/package-lock.json",
        "frontend/package.json",
        "frontend/scripts/generate-api-types.mjs",
        "frontend/src/app/App.test.tsx",
        "frontend/src/app/App.tsx",
        "frontend/src/app/main.tsx",
        "frontend/src/app/styles.css",
        "frontend/src/entities/.gitkeep",
        "frontend/src/features/.gitkeep",
        "frontend/src/pages/home/index.ts",
        "frontend/src/pages/home/ui/HomePage.tsx",
        "frontend/src/pages/not-found/index.ts",
        "frontend/src/pages/not-found/ui/NotFoundPage.tsx",
        "frontend/src/shared/api/api.test.ts",
        "frontend/src/shared/api/generated/.gitkeep",
        "frontend/src/shared/api/index.ts",
        "frontend/src/test/setup.ts",
        "frontend/src/widgets/.gitkeep",
        "frontend/tsconfig.json",
        "frontend/vite.config.ts",
        "frontend/vitest.config.ts"
      ],
      "tests": {
        "passed": 4,
        "failed": 0
      },
      "commit": "c25b6a9",
      "concerns": [],
      "startedAt": "2026-11-11T05:09:51+03:00",
      "finishedAt": "2026-11-11T06:33:12+03:00"
    },
    {
      "id": "03",
      "title": "Compose runtime and clean setup guide",
      "requirements": [
        "R21",
        "R22",
        "R24",
        "R26",
        "R27",
        "R28",
        "R29",
        "R34",
        "R35",
        "R33",
        "R38",
        "R39",
        "R40",
        "R41",
        "R42",
        "R43",
        "R44",
        "R45",
        "R46",
        "R47",
        "R48",
        "R49",
        "R50",
        "R51",
        "R52",
        "R53",
        "R54"
      ],
      "blockedBy": [
        "01",
        "02"
      ],
      "wave": 3,
      "zone": [
        "docker-compose.yml",
        "infra/",
        ".env.example",
        "README.md",
        "docs/operations/LOCAL_DEVELOPMENT.md"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 1,
      "repairFindings": [
        "POSIX port extraction retained CR from Windows CRLF .env; health/schema curl commands then targeted localhost port 80. Fix both extraction sites and verify the documented POSIX commands."
      ],
      "handoffs": 0,
      "tests": {
        "passed": 17,
        "failed": 0
      },
      "commit": "bc86782",
      "concerns": [
        "Host port 8000 is occupied by unrelated travel-architecture-check-backend-1; full Compose acceptance ran on BACKEND_HOST_PORT=8001 and clean-machine default remains 8000."
      ],
      "startedAt": "2026-11-11T06:34:05+03:00",
      "files": [
        "docker-compose.yml",
        "infra/docker/backend.Dockerfile",
        "infra/docker/backend.Dockerfile.dockerignore",
        "infra/docker/frontend.Dockerfile",
        "infra/docker/frontend.Dockerfile.dockerignore",
        ".env.example",
        "README.md",
        "docs/operations/LOCAL_DEVELOPMENT.md"
      ],
      "finishedAt": "2026-11-11T12:34:15+03:00"
    },
    {
      "id": "04",
      "title": "Bind the frontend development port locally",
      "requirements": [
        "R24",
        "R40"
      ],
      "blockedBy": [
        "03"
      ],
      "wave": 4,
      "zone": [
        "docker-compose.yml"
      ],
      "status": "done",
      "retries": 0,
      "repairs": 0,
      "repairFindings": [],
      "handoffs": 0,
      "files": [
        "docker-compose.yml"
      ],
      "tests": {
        "passed": 2,
        "failed": 0
      },
      "commit": "ac1880e",
      "concerns": [],
      "startedAt": "2026-11-11T12:34:15+03:00",
      "finishedAt": "2026-11-11T12:37:42+03:00"
    }
  ],
  "singlePass": null,
  "tests": {
    "passed": 17,
    "failed": 0
  },
  "debt": {
    "emptyEnv": [],
    "placeholders": [],
    "assumptions": []
  },
  "additions": [],
  "coverage": {
    "found": 1,
    "fixed": 1,
    "deferred": 0
  },
  "concerns": [
    "Dropped after verification: backend/apps/common/tests/test_tasks.py uses the eager-mode unit seam specified for the task; the real Compose worker probe returned status ok.",
    "Report: backend/apps/health/tests/test_readiness.py mocks dependencies and does not directly cover query-execution failure; live PostgreSQL/Redis readiness passed.",
    "Report: host port 8000 is occupied by unrelated travel-architecture-check-backend-1; this workspace uses the documented BACKEND_HOST_PORT=8001 override."
  ],
  "reviewers": {
    "craft": "/root/review_ticket01_craft",
    "manifestSpec": "/root/review_ticket01_manifest_spec"
  },
  "blind": {
    "status": "passed",
    "checkedAt": "2026-11-11T12:49:13+03:00",
    "verdict": "All Stage 01 acceptance criteria are realized; no disagreements or blockers.",
    "disagreements": [],
    "evidence": [
      "All five Compose services healthy; backend readiness reported PostgreSQL and Redis ok.",
      "Frontend, API health, schema, docs, HTTP and WebSocket Vite proxies passed; WebSocket closed with code 1000.",
      "pgvector extension present; real Celery task returned status ok; live type generation produced 4,221 bytes.",
      "Database and media markers survived ordinary down/up; markers were removed afterward and volumes retained.",
      "No business models or product workflows; Celery Beat absent and deferred."
    ],
    "commands": [
      "docker compose up --build -d",
      "docker compose up -d --wait",
      "docker compose ps",
      "docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest",
      "docker compose exec frontend npm test"
    ]
  }
};
