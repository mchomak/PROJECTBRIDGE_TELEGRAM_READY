window.STATE =
{
    "slug":  "stage02-accounts-authentication",
    "dir":  "2026-11-11-stage02-accounts-authentication",
    "title":  "ProjectBridge Stage 02 — Accounts and Authentication",
    "mode":  "full",
    "depth":  "normal",
    "polish":  null,
    "tier":  "T2",
    "briefFile":  "2026-11-11-brief.md",
    "memoryFile":  "AGENTS.md",
    "skillDir":  "C:/Users/McHomak/.agents/skills/autopilot",
    "startedAt":  "2026-11-11T15:40:07+03:00",
    "updatedAt":  "2026-11-11T21:22:56+03:00",
    "finishedAt":  "2026-11-11T21:22:56+03:00",
    "stages":  [
                   {
                       "id":  "preflight",
                       "status":  "done",
                       "startedAt":  "2026-11-11T15:40:07+03:00",
                       "finishedAt":  "2026-11-11T15:40:07+03:00"
                   },
                   {
                       "id":  "manifest",
                       "status":  "done",
                       "startedAt":  "2026-11-11T15:40:07+03:00",
                       "finishedAt":  "2026-11-11T15:53:07+03:00"
                   },
                   {
                       "id":  "briefing",
                       "status":  "skipped",
                       "reason":  "Full mode self-briefing; no user interview.",
                       "note":  "Product and migration assumptions recorded in the manifest."
                   },
                   {
                       "id":  "spec",
                       "status":  "done",
                       "startedAt":  "2026-11-11T15:53:07+03:00",
                       "finishedAt":  "2026-11-11T16:06:53+03:00",
                       "note":  "G2 passed: all source documents listed; CSRF covers unsafe methods; implementation choices attached to parent requirements."
                   },
                   {
                       "id":  "plan",
                       "status":  "done",
                       "startedAt":  "2026-11-11T16:06:53+03:00",
                       "finishedAt":  "2026-11-11T16:14:22+03:00",
                       "note":  "T2: 4 запланированных таска в 3 волнах; ticket 05 закрыл finding финального ревью"
                   },
                   {
                       "id":  "build",
                       "status":  "done",
                       "startedAt":  "2026-11-11T16:14:22+03:00",
                       "note":  "5 из 5 тасков готовы",
                       "finishedAt":  "2026-11-11T21:22:56+03:00"
                   },
                   {
                       "id":  "review",
                       "status":  "done",
                       "startedAt":  "2026-11-11T17:23:35+03:00",
                       "note":  "5 из 5 прошли ревью; G4 прошёл",
                       "finishedAt":  "2026-11-11T21:22:56+03:00"
                   },
                   {
                       "id":  "final",
                       "status":  "done",
                       "startedAt":  "2026-11-11T21:15:09+03:00",
                       "note":  "G4 пройден; проектная память и ADR записаны; панель пропущена по просьбе пользователя",
                       "finishedAt":  "2026-11-11T21:22:56+03:00"
                   }
               ],
    "requirements":  {
                         "total":  59,
                         "done":  53,
                         "inTicket":  0,
                         "inSpec":  0,
                         "placeholder":  0,
                         "deferred":  6,
                         "dropped":  0
                     },
    "tickets":  [
                    {
                        "id":  "01",
                        "title":  "Модель аккаунта и migration plan",
                        "requirements":  [
                                             "R01",
                                             "R02",
                                             "R03",
                                             "R04",
                                             "R11",
                                             "R12",
                                             "R13",
                                             "R14",
                                             "R34",
                                             "R41",
                                             "R42",
                                             "R44",
                                             "R54",
                                             "R55",
                                             "R56",
                                             "R57",
                                             "R59"
                                         ],
                        "blockedBy":  [

                                      ],
                        "wave":  1,
                        "zone":  [
                                     "backend/apps/accounts/",
                                     "backend/apps/common/api/",
                                     "backend/config/settings/",
                                     "backend/config/urls.py",
                                     ".env.example",
                                     "docker-compose.yml",
                                     "docs/database/",
                                     "docs/adr/",
                                     "backend/requirements.txt",
                                     "backend/config/tests/test_production_settings.py"
                                 ],
                        "status":  "done",
                        "retries":  1,
                        "repairs":  2,
                        "repairFindings":  [
                                               "Backend full suite red: config/tests/test_production_settings.py::test_production_disables_debug_and_development_documentation_routes fails because production settings require FRONTEND_BASE_URL.",
                                               "Active config.settings.local uses AUTH_USER_MODEL=auth.User and showmigrations accounts reports no migrations; the configured custom user model/migration is not active in the local runtime."
                                           ],
                        "handoffs":  2,
                        "startedAt":  "2026-11-11T16:17:09+03:00",
                        "finishedAt":  "2026-11-11T18:09:33+03:00",
                        "files":  [
                                      ".env.example",
                                      "docker-compose.yml",
                                      "backend/requirements.txt",
                                      "backend/config/urls.py",
                                      "backend/config/settings/base.py",
                                      "backend/config/settings/local.py",
                                      "backend/config/settings/production.py",
                                      "backend/config/settings/test.py",
                                      "backend/config/tests/test_production_settings.py",
                                      "backend/config/tests/test_auth_url_scaffolding.py",
                                      "backend/apps/accounts/models.py",
                                      "backend/apps/accounts/services.py",
                                      "backend/apps/accounts/migrations/0001_initial.py",
                                      "backend/apps/accounts/migrations/__init__.py",
                                      "backend/apps/accounts/tests/test_models.py",
                                      "backend/apps/accounts/api/__init__.py",
                                      "backend/apps/accounts/api/urls.py",
                                      "backend/apps/accounts/api/core_urls.py",
                                      "backend/apps/accounts/api/verification_urls.py",
                                      "backend/apps/common/api/__init__.py",
                                      "backend/apps/common/api/errors.py",
                                      "backend/apps/common/tests/test_api_errors.py",
                                      "docs/database/DATA_MODEL.md",
                                      "docs/adr/0005-additive-accounts-user-migration.md"
                                  ],
                        "tests":  {
                                      "passed":  31,
                                      "failed":  0
                                  },
                        "commit":  "7265d78"
                    },
                    {
                        "id":  "02",
                        "title":  "Session auth API",
                        "requirements":  [
                                             "R05",
                                             "R06",
                                             "R07",
                                             "R08",
                                             "R15",
                                             "R16",
                                             "R17",
                                             "R20",
                                             "R35",
                                             "R37",
                                             "R40",
                                             "R41",
                                             "R42",
                                             "R43",
                                             "R46",
                                             "R47",
                                             "R48",
                                             "R50",
                                             "R51",
                                             "R53",
                                             "R59"
                                         ],
                        "blockedBy":  [
                                          "01"
                                      ],
                        "wave":  2,
                        "zone":  [
                                     "backend/apps/accounts/api/core/",
                                     "backend/apps/accounts/api/core_urls.py",
                                     "backend/apps/accounts/tests/api/test_auth.py",
                                     "docs/api/",
                                     "docs/security/",
                                     "docs/OPEN_DECISIONS.md"
                                 ],
                        "status":  "done",
                        "retries":  0,
                        "repairs":  0,
                        "repairFindings":  [

                                           ],
                        "handoffs":  1,
                        "startedAt":  "2026-11-11T18:11:05+03:00",
                        "finishedAt":  "2026-11-11T19:06:57+03:00",
                        "files":  [
                                      "backend/apps/accounts/api/core/__init__.py",
                                      "backend/apps/accounts/api/core/permissions.py",
                                      "backend/apps/accounts/api/core/serializers.py",
                                      "backend/apps/accounts/api/core/views.py",
                                      "backend/apps/accounts/api/core_urls.py",
                                      "backend/apps/accounts/tests/api/test_auth.py",
                                      "docs/api/API_CONTRACT.md",
                                      "docs/security/ACCESS_CONTROL_AND_SECURITY.md",
                                      "docs/OPEN_DECISIONS.md"
                                  ],
                        "tests":  {
                                      "passed":  55,
                                      "failed":  0
                                  },
                        "commit":  "96e6c61"
                    },
                    {
                        "id":  "03",
                        "title":  "Email verification API",
                        "requirements":  [
                                             "R09",
                                             "R10",
                                             "R11",
                                             "R12",
                                             "R13",
                                             "R14",
                                             "R18",
                                             "R19",
                                             "R35",
                                             "R36",
                                             "R39",
                                             "R44",
                                             "R45",
                                             "R46",
                                             "R52",
                                             "R53",
                                             "R59"
                                         ],
                        "blockedBy":  [
                                          "01"
                                      ],
                        "wave":  2,
                        "zone":  [
                                     "backend/apps/accounts/api/verification/",
                                     "backend/apps/accounts/api/verification_urls.py",
                                     "backend/apps/accounts/tests/api/test_verification.py"
                                 ],
                        "status":  "done",
                        "retries":  0,
                        "repairs":  0,
                        "repairFindings":  [

                                           ],
                        "handoffs":  0,
                        "startedAt":  "2026-11-11T18:11:05+03:00",
                        "finishedAt":  "2026-11-11T19:21:09+03:00",
                        "files":  [
                                      "backend/apps/accounts/api/verification/__init__.py",
                                      "backend/apps/accounts/api/verification/serializers.py",
                                      "backend/apps/accounts/api/verification/views.py",
                                      "backend/apps/accounts/api/verification_urls.py",
                                      "backend/apps/accounts/tests/api/test_verification.py"
                                  ],
                        "tests":  {
                                      "passed":  55,
                                      "failed":  0
                                  },
                        "commit":  "11d4c1c"
                    },
                    {
                        "id":  "04",
                        "title":  "Frontend auth flows and route guards",
                        "requirements":  [
                                             "R21",
                                             "R23",
                                             "R24",
                                             "R25",
                                             "R26",
                                             "R27",
                                             "R28",
                                             "R38",
                                             "R39",
                                             "R43",
                                             "R49",
                                             "R53",
                                             "R59"
                                         ],
                        "blockedBy":  [
                                          "02",
                                          "03"
                                      ],
                        "wave":  3,
                        "zone":  [
                                     "frontend/src/",
                                     "frontend/package.json",
                                     "frontend/package-lock.json",
                                     "docs/architecture/FRONTEND_ARCHITECTURE.md"
                                 ],
                        "status":  "done",
                        "retries":  0,
                        "repairs":  0,
                        "repairFindings":  [

                                           ],
                        "handoffs":  1,
                        "startedAt":  "2026-11-11T19:25:44+03:00",
                        "finishedAt":  "2026-11-11T20:31:08+03:00",
                        "files":  [
                                      "docs/architecture/FRONTEND_ARCHITECTURE.md",
                                      "frontend/src/app/App.test.tsx",
                                      "frontend/src/app/App.tsx",
                                      "frontend/src/entities/user/index.ts",
                                      "frontend/src/entities/user/model/currentUser.ts",
                                      "frontend/src/entities/user/model/types.ts",
                                      "frontend/src/features/auth/index.ts",
                                      "frontend/src/features/auth/model/authActions.ts",
                                      "frontend/src/pages/auth/index.ts",
                                      "frontend/src/pages/auth/ui/LoginPage.tsx",
                                      "frontend/src/pages/auth/ui/RegisterPage.tsx",
                                      "frontend/src/pages/auth/ui/VerificationRequiredPage.tsx",
                                      "frontend/src/pages/auth/ui/VerifyEmailPage.tsx",
                                      "frontend/src/shared/api/api.test.ts",
                                      "frontend/src/shared/api/generated/schema.d.ts",
                                      "frontend/src/shared/api/index.ts"
                                  ],
                        "tests":  {
                                      "passed":  70,
                                      "failed":  0
                                  },
                        "commit":  "7c0cb4c"
                    },
                    {
                        "id":  "05",
                        "title":  "Verification email status copy",
                        "requirements":  [
                                             "R22"
                                         ],
                        "blockedBy":  [
                                          "04"
                                      ],
                        "wave":  4,
                        "zone":  [
                                     "frontend/src/pages/auth/",
                                     "frontend/src/app/App.test.tsx"
                                 ],
                        "status":  "done",
                        "retries":  0,
                        "repairs":  0,
                        "repairFindings":  [

                                           ],
                        "handoffs":  0,
                        "startedAt":  "2026-11-11T20:32:22+03:00",
                        "finishedAt":  "2026-11-11T20:54:53+03:00",
                        "files":  [
                                      "frontend/src/app/App.test.tsx",
                                      "frontend/src/pages/auth/ui/VerificationRequiredPage.tsx"
                                  ],
                        "tests":  {
                                      "passed":  70,
                                      "failed":  0
                                  },
                        "commit":  "6a1f85e"
                    }
                ],
    "singlePass":  null,
    "tests":  {
                  "passed":  70,
                  "failed":  0
              },
    "debt":  {
                 "placeholders":  [

                                  ],
                 "assumptions":  [
                                     "Email is normalized by trimming and Unicode casefolding the entire address.",
                                     "accounts.User extends AbstractUser, uses UUID, email_verified_at, and an email-only manager; names are optional and blank.",
                                     "Registration accepts only email/password, creates no session, and requires an explicit login after verification.",
                                     "Unverified users may log in only to complete verification; frontend product routes remain guarded until verified.",
                                     "Password validation uses standard Django validators with a minimum of 8 characters; Argon2 is first when supported by pinned Python 3.13.",
                                     "Verification tokens use 256-bit entropy, SHA-256 digests, a 24-hour TTL, and resend rotates earlier active tokens.",
                                     "Verification links use FRONTEND_BASE_URL with a URL fragment; local default is http://localhost:5173 and production sets its own origin.",
                                     "Initial auth limits are register 5/hour, login 10/minute, resend 3/hour, confirm 10/hour using Redis-backed scoped throttling.",
                                     "Registration reports a duplicate email; login, resend, and token errors avoid extra account enumeration.",
                                     "Cookie SameSite is Lax; production session and CSRF cookies are Secure.",
                                     "Auth pages use /login, /register, /verify-email, /verification-required, /app; expired 401 clears current-user state and redirects to login, while network failures remain retryable."
                                 ],
                 "emptyEnv":  [

                              ]
             },
    "additions":  [

                  ],
    "coverage":  {
                     "found":  14,
                     "fixed":  14,
                     "deferred":  0,
                     "findings":  [
                                      {
                                          "kind":  "missing",
                                          "issue":  "Read-first source documents were not enumerated in the spec.",
                                          "action":  "Added the full source document list."
                                      },
                                      {
                                          "kind":  "half-covered",
                                          "issue":  "CSRF scope only named POST.",
                                          "action":  "Expanded spec to all unsafe methods: POST, PUT, PATCH, DELETE."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Custom model and migration detail.",
                                          "action":  "Attached to R01/R34/R54/R55 and the database contract."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Email normalization rule.",
                                          "action":  "Recorded as ASSUMPTION under R02."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Password validators.",
                                          "action":  "Recorded as ASSUMPTION under R03."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Token entropy, hash, TTL, rotation, and row locking.",
                                          "action":  "Recorded as ASSUMPTION/deepening under R11-R14."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Endpoint paths, payloads, and statuses.",
                                          "action":  "Tied paths to API_CONTRACT; payload choices recorded under R05-R10."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Email URL and token fragment.",
                                          "action":  "Recorded as ASSUMPTION under R18/R23."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Cookie SameSite and anonymous CSRF bootstrap.",
                                          "action":  "Recorded under R16/R17; SameSite marked ASSUMPTION."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Redis and initial throttle rates.",
                                          "action":  "Recorded as ASSUMPTION under R19."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Error envelope and 401/403 status mapping.",
                                          "action":  "Tied to API_CONTRACT under R20."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Frontend routes, query state, token handling, and accessibility.",
                                          "action":  "Attached to R21-R28/R38; route/token choices marked ASSUMPTION."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Expired session versus network failure UI behavior.",
                                          "action":  "Recorded as ASSUMPTION under R26."
                                      },
                                      {
                                          "kind":  "parented-detail",
                                          "issue":  "Persistent auth storage and test seams.",
                                          "action":  "Kept the localStorage prohibition from R28 and tied test tools to existing project suites under R39."
                                      }
                                  ]
                 },
    "concerns":  [
                     "Report (nonblocking coverage): backend/apps/accounts/tests/test_models.py:69 checks duplicate registration sequentially, not under concurrent calls; the DB unique constraint still rejects duplicates.",
                     "Report (nonblocking coverage): backend/apps/accounts/tests/test_models.py:140 checks token reuse sequentially, not concurrent confirmation; service uses row locking.",
                     "Report (nonblocking coverage): backend/apps/accounts/tests/api/test_auth.py:123 checks OpenAPI schema presence but not every credential/CSRF/UserSummary field.",
                     "Report (nonblocking coverage): backend/apps/accounts/tests/api/test_auth.py:224 uses one account for /me rather than two sessions.",
                     "Report (nonblocking coverage): backend/apps/accounts/tests/api/test_auth.py:383 asserts registration throttling but not login throttling.",
                     "Report (nonblocking coverage): backend/apps/accounts/tests/api/test_verification.py:187 does not assert raw token absence from successful confirmation response.",
                     "Report (nonblocking coverage): backend/apps/accounts/tests/api/test_verification.py:62 does not assert resend recipient eligibility.",
                     "Report (nonblocking coverage): backend/apps/accounts/tests/api/test_verification.py:459 checks partial OpenAPI fields and not resend requiredness.",
                     "Report (nonblocking coverage): backend/apps/accounts/tests/api/test_verification.py:94 authenticated resend tests disable CSRF checks.",
                     "Resolved in ticket 05 (commit 6a1f85e): unverified-login copy no longer claims a verification email was sent.",
                     "Dropped: suspected CSRF-cookie leakage between frontend tests did not reproduce in repeated full 19-test frontend suites."
                 ],
    "reviewers":  {
                      "manifestSpec":  "/root/manifest_spec_reviewer",
                      "craft":  "/root/craft_reviewer"
                  },
    "blind":  {
                  "status":  "passed",
                  "checkedAt":  "2026-11-11T21:15:09+03:00",
                  "verdict":  "All in-scope Stage 02 requirements are implemented; no G4 disagreements.",
                  "disagreements":  [

                                    ],
                  "evidence":  [
                                   "All five Compose services healthy; frontend, health and OpenAPI endpoints returned 200; anonymous current-user returned 401.",
                                   "Django runtime uses accounts.User and accounts.0001_initial is applied; Argon2 is preferred; console email backend is configured.",
                                   "Root browser flow registered a disposable account and confirmed its email through the URL fragment; the account and token rows were removed after the check.",
                                   "Live auth routes render; unauthenticated /app redirects to /login. Tests cover session, CSRF, token expiration/reuse, throttling, validation, network errors and no localStorage writes.",
                                   "Backend 51 tests and frontend 19 tests pass; all required static and build checks pass."
                               ],
                  "commands":  [
                                   "docker compose ps — all five services healthy",
                                   "docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q — 51 passed",
                                   "docker compose exec frontend npm test — 19 passed",
                                   "docker compose run --rm --no-deps backend ruff format --check . — passed",
                                   "docker compose run --rm --no-deps backend ruff check . — passed",
                                   "docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test backend python manage.py makemigrations --check --dry-run — no changes detected",
                                   "docker compose exec frontend npm run format:check — passed",
                                   "docker compose exec frontend npm run lint — passed",
                                   "docker compose exec frontend npm run typecheck — passed",
                                   "docker compose exec frontend npm run build — passed",
                                   "docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types — passed"
                               ]
              }
}
