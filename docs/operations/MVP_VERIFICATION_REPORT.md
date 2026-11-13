# Stage 13 MVP Verification Report

**Run date:** 2026-11-13
**Scope:** Stage 13 integration and hardening, including the dispatch recovery
work used by documents, AI analysis, and specification generation. This report
records verification evidence for the stage coordinator.

## End-to-end coverage

`backend/apps/common/tests/test_stage13_mvp_workflow.py::test_stage13_two_member_workflow_through_public_apis_and_real_sessions`
uses two CSRF-enforced REST clients with real Django session cookies and
locmem email. The scenario registers and verifies both users, creates a
project, sends and accepts an email-bound invitation, submits the product
questionnaire, maps answers to the passport, exercises shared Project State,
and exchanges persisted chat messages. It verifies that a project member's
WebSocket receives a REST-created message and that a nonmember is rejected.

The same scenario uploads, extracts, and embeds a document, then runs analysis
while it is active. The test resolves the retrieved `document_chunk` evidence
ID to a chunk belonging to that uploaded document, verifies the AI proposal
cites the same source ID and excerpt, and only then archives it. A second
analysis verifies archived-document chunks are absent from retrieved evidence
while the stored chunk still exists. The scenario also downloads, restores,
and mutually deletes the document; applies the proposal only after executor
approval; generates a deterministic specification; and completes, archives,
restores, and reopens the project.
The customer is denied executor-only Project State, AI, and specification
actions, and receives no private AI history or generation details. The test
uses a deterministic no-cost AI adapter and locmem email; it does not contact
paid providers or send external messages. Test-only AI profile configuration
is fixture setup; user, project, invitation, questionnaire, state, chat,
document, AI, specification, and lifecycle workflow changes go through public
REST endpoints.

## Durable dispatch policy

The documents, AI analysis, and specification queues all distinguish publish
exceptions from dispatch reservations. A publisher exception is ambiguous: it
may occur after broker acceptance. Recovery therefore keeps queued work
nonterminal, retains the same task ID for the current generation, and never
fences an older message that may already be at the FIFO head. The stored
exception counter saturates at 12; retries use exponential backoff from 30
seconds to 30 minutes. Five publish exceptions expose `queue_unavailable`
without failing the work. Five dispatch reservations without a worker claim
expose the separate nonterminal `worker_backlog` warning. A worker claim clears
either warning.

Regression tests cover a fake publisher that records a message and then raises
five times, followed by processing of the oldest FIFO message exactly once;
successful publish followed by a failed dispatch-marker save; and successful
publishes without a worker claim followed by warning and claim recovery. The
tests cover all three queues. Document success and failure markers are fenced
by the captured dispatch attempt and `processing_generation`; the delayed
callback regression reclaims generation 0 into generation 1, reuses attempt 1,
and verifies the old generation's success or failure marker cannot alter the
new dispatch state. The emitted task IDs are asserted as generation-scoped.
UI tests verify both warnings are visible, use neutral waiting/retry copy, and
disappear after recovery. Document queries
poll every three seconds only while a visible document is queued or
processing, then stop when its processing state is terminal.

## Verification commands and results

| Command | Result |
|:--|:--|
| `docker compose run --build --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test -e DB_NAME=stage13_target_20261113 backend python -m pytest -q apps/common/tests/test_stage13_mvp_workflow.py apps/documents/tests/test_processing.py -k "stage13_two_member_workflow or delayed_document_dispatch_callback"` | **3 passed**, 28 deselected in 4.94 s |
| `docker compose run --build --rm --no-deps -e DJANGO_SETTINGS_MODULE=config.settings.test -e DB_NAME=stage13_full_20261113 backend python -m pytest -q` | **441 passed** in 31.20 s |
| `docker compose run --rm --no-deps backend ruff format --check apps/common/tests/test_stage13_mvp_workflow.py apps/documents/tests/test_processing.py` | **2 files already formatted** |
| `docker compose run --rm --no-deps backend ruff check apps/common/tests/test_stage13_mvp_workflow.py apps/documents/tests/test_processing.py` | **All checks passed** |
| `docker compose run --rm --no-deps backend ruff format --check .` | **215 files already formatted** |
| `docker compose run --rm --no-deps backend ruff check .` | **All checks passed** |
| `docker compose run --rm --no-deps backend python manage.py makemigrations --check --dry-run` | **No changes detected** |
| `docker compose exec backend python manage.py spectacular --validate --file /tmp/openapi.yml` | **Passed** (exit 0) |
| `docker compose exec -e API_SCHEMA_URL=http://backend:8000/api/schema/ frontend npm run api:types` followed by `docker compose cp frontend:/app/src/shared/api/generated/schema.d.ts frontend/src/shared/api/generated/schema.d.ts` | **Passed**; generated types include `processing_dispatch_error_code` |
| `docker compose exec frontend npm run format:check` | **Passed**; 103 files checked |
| `docker compose exec frontend npm run lint` | **Passed**; 104 files checked |
| `docker compose exec frontend npm run typecheck` | **Passed** |
| `docker compose run --rm --no-deps frontend npm test` | **97 passed**, 12 files |
| `docker compose exec frontend npm run build` | **Passed**; Vite production build completed |
| `docker compose config --quiet` | **Passed** |

### Clean database and restart checks

A uniquely named scratch database (`stage13_migration_scratch_20261113`)
was created only after confirming it did not exist. The clean migration command
was:

```text
docker compose run --rm --no-deps -e DB_NAME=stage13_migration_scratch_20261113 backend python manage.py migrate --noinput
```

All migrations succeeded, including AI assistant migrations 0008 and 0009,
documents migrations 0006 through 0008, and specification migration 0003.
After confirming there were no active connections, only this scratch database
was dropped. The live database received the additive documents 0008 migration
with `docker compose exec backend python manage.py migrate`.

`docker compose up --build -d` rebuilt and started all six services.
Persistence was then checked across `docker compose restart`: a temporary
database marker and a file in `/app/media` both survived restart, and
`/api/v1/health/` returned 200. Both temporary markers were verified and
removed. The named volumes `projectbridge_postgres_data` and
`projectbridge_media` were preserved; `docker compose down -v` was not run.

## Security audit and limits

The local secret audit checked that `.env` is not Git-tracked, compared the
configured Django/database/Redis/OpenAI secret values against backend, worker,
and Beat logs and frontend source/build output, scanned logs/assets for
credential-shaped values, and checked logs for the E2E document/AI fixture
text. It found no matches. No `.env` values were printed. REST and WebSocket
membership boundaries, cross-project isolation, customer access to AI-private
data, document sharing, and executor approval before applying proposals are
covered by the integration scenario and backend suite.

Live OpenAI credentials and paid API calls were not exercised. All integration
provider calls used deterministic fakes. Email used Django's local console
backend or test locmem backend; production email delivery was not exercised.
These are deliberate local-MVP verification limits, not claims about live
provider availability.

No Stage 13 implementation question remains blocking local workflow
verification. Before public onboarding, resolve the existing decisions in
`docs/OPEN_DECISIONS.md` for malware scanning (#28), privacy and consent (#29),
external AI disclosure and provider terms (#30), operational log retention
(#31), production secret management (#34), hosting (#35), production email
(#37), and object storage (#38). Backup restoration (#33) and monitoring
(#36) also remain production-readiness work. Do not present the local MVP as
ready for public customer onboarding while the privacy and external-AI
disclosures remain unresolved.
