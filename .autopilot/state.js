window.STATE =
{
    "slug":  "repository-baseline",
    "dir":  "2026-11-11-repository-baseline",
    "title":  "ProjectBridge Stage 00 — Repository Baseline and Tooling",
    "mode":  "full",
    "depth":  "normal",
    "polish":  null,
    "tier":  "T0",
    "briefFile":  "2026-11-11-brief.md",
    "memoryFile":  "AGENTS.md",
    "skillDir":  "C:/Users/McHomak/.agents/skills/autopilot",
    "startedAt":  "2026-11-11T02:18:27+03:00",
    "updatedAt":  "2026-11-11T03:11:51+03:00",
    "finishedAt":  "2026-11-11T03:11:51+03:00",
    "stages":  [
                   {
                       "id":  "preflight",
                       "status":  "done",
                       "startedAt":  "2026-11-11T02:18:27+03:00",
                       "finishedAt":  "2026-11-11T02:25:50+03:00"
                   },
                   {
                       "id":  "manifest",
                       "status":  "done",
                       "note":  "21 requirements; 19 implemented, 2 deferred."
                   },
                   {
                       "id":  "briefing",
                       "status":  "skipped",
                       "reason":  "full mode self-briefing; no interview questions remained",
                       "note":  "Full mode self-briefing; no interview questions remained."
                   },
                   {
                       "id":  "spec",
                       "status":  "done",
                       "note":  "G2 coverage check passed."
                   },
                   {
                       "id":  "plan",
                       "status":  "skipped",
                       "note":  "Tier T0; one single-pass assignment."
                   },
                   {
                       "id":  "build",
                       "status":  "done",
                       "finishedAt":  "2026-11-11T03:11:51+03:00",
                       "note":  "Repository setup complete; no application code added."
                   },
                   {
                       "id":  "review",
                       "status":  "done",
                       "finishedAt":  "2026-11-11T03:11:51+03:00",
                       "note":  "Independent acceptance and repository checks passed."
                   },
                   {
                       "id":  "final",
                       "status":  "done",
                       "startedAt":  "2026-11-11T03:11:51+03:00",
                       "finishedAt":  "2026-11-11T03:11:51+03:00"
                   }
               ],
    "requirements":  {
                         "total":  21,
                         "done":  19,
                         "inTicket":  0,
                         "inSpec":  0,
                         "placeholder":  0,
                         "deferred":  2,
                         "dropped":  0
                     },
    "tickets":  [

                ],
    "singlePass":  {
                       "requirements":  [
                                            "R01",
                                            "R02",
                                            "R03",
                                            "R04",
                                            "R05",
                                            "R06",
                                            "R07",
                                            "R08",
                                            "R09",
                                            "R10",
                                            "R12",
                                            "R13",
                                            "R14",
                                            "R15",
                                            "R16",
                                            "R17",
                                            "R18",
                                            "R20",
                                            "G01"
                                        ],
                       "status":  "done",
                       "startedAt":  "2026-11-11T02:39:46+03:00",
                       "files":  [
                                     ".gitignore",
                                     ".env.example",
                                     "README.md",
                                     "frontend/.gitkeep",
                                     "backend/.gitkeep",
                                     "infra/.gitkeep",
                                     "scripts/.gitkeep",
                                     "docs/README.md",
                                     "docs/product/MVP_SCOPE.md",
                                     "docs/architecture/SYSTEM_ARCHITECTURE.md",
                                     "docs/architecture/FRONTEND_ARCHITECTURE.md",
                                     "docs/architecture/BACKEND_ARCHITECTURE.md",
                                     "docs/database/DATA_MODEL.md",
                                     "docs/api/API_CONTRACT.md",
                                     "docs/ai/AI_ARCHITECTURE.md",
                                     "docs/security/ACCESS_CONTROL_AND_SECURITY.md",
                                     "docs/documents/DOCUMENT_LIFECYCLE.md",
                                     "docs/operations/LOCAL_DEVELOPMENT.md",
                                     "docs/implementation/DEVELOPMENT_ROADMAP.md",
                                     "docs/decisions/ADR-001-MONOREPO.md",
                                     "docs/decisions/ADR-002-MODULAR-MONOLITH.md",
                                     "docs/decisions/ADR-003-FEATURE-SLICED-FRONTEND.md",
                                     "docs/decisions/ADR-004-POSTGRESQL-DATA-MODEL.md",
                                     "docs/decisions/ADR-005-REST-WEBSOCKET-OPENAPI.md",
                                     "docs/decisions/ADR-006-AI-PROVIDER-ROUTING.md",
                                     "docs/decisions/ADR-007-SHARED-DOCUMENT-LIFECYCLE.md",
                                     "docs/decisions/ADR-008-PROJECT-ACCESS-CONTROL.md",
                                     "AGENTS.md"
                                 ],
                       "tests":  null,
                       "commit":  null,
                       "finishedAt":  "2026-11-11T03:11:51+03:00",
                       "repairs":  1,
                       "repairFindings":  [
                                              "README listed no planned format/lint/test commands; added explicit Stage 01 command names."
                                          ]
                   },
    "tests":  null,
    "debt":  {
                 "placeholders":  [

                                  ],
                 "assumptions":  [
                                     "Move the existing root technical index to docs/README.md and preserve its content.",
                                     "Use npm for the future frontend and Python venv plus pip for the future backend because no manifests or lockfiles existed.",
                                     "Keep the HTML MVP mockup at the root unchanged as a product and visual reference.",
                                     "Defer runnable app tooling and app-internal structure to Stage 01; list planned quality command names in README."
                                 ],
                 "emptyEnv":  [
                                  "DJANGO_SECRET_KEY",
                                  "DJANGO_DEBUG",
                                  "DATABASE_URL",
                                  "REDIS_URL",
                                  "ALLOWED_HOSTS",
                                  "CSRF_TRUSTED_ORIGINS",
                                  "FRONTEND_BASE_URL",
                                  "FILE_STORAGE_ROOT",
                                  "AI_PROVIDER",
                                  "AI_PROVIDER_API_KEY",
                                  "AI_MODEL"
                              ]
             },
    "additions":  [

                  ],
    "coverage":  {
                     "count":  0,
                     "findings":  [

                                  ],
                     "result":  "PASS"
                 },
    "concerns":  [

                 ],
    "reviewers":  {
                      "manifestSpec":  null,
                      "craft":  null
                  },
    "blind":  {
                  "result":  "PASS",
                  "summary":  "Blind acceptance found no unimplemented Stage 00 requirement; Stage 01 owns internal app directories and runnable app tooling.",
                  "findings":  [

                               ]
              }
}
