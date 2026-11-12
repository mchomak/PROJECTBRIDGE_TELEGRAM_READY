СДЕЛАНО: Preview and acceptance backend core implemented; targeted safe-state/auth/replay/isolation/rate checks partly covered.
ФАЙЛЫ: backend/apps/invitations/services.py, api serializers/views/urls/public_urls, backend/config/urls.py, backend/apps/projects/services.py and service/API tests.
ФАЙЛЫ: T01 issuance/list/revoke logic was left intact; public preview/accept routes were added beside it.
РЕШЕНИЯ: Preview returns only project name, masked email hint, expiry, and invitation status.
РЕШЕНИЯ: Unknown tokens return 404; expired/revoked return 410; completed/archived return distinct 409 codes per spec §5.
РЕШЕНИЯ: Acceptance locks/writes through projects.services.add_customer_member_from_invitation; invitation update and both audit writes share its outer transaction.
РЕШЕНИЯ: Rate limits use fixed UTC-hour cache buckets: preview by REMOTE_ADDR at 30/hour, acceptance by user at 10/hour.
ТУПИКИ: First pytest path was wrong for the container; use apps/... from /app, not backend/apps/....
ТУПИКИ: Do not use status 410 for closed projects; root confirmed §5 reserves it for expired/revoked invitations.
ДАЛЬШЕ: Add concurrency/transaction rollback and active-project acceptance checks at the invitation API/service seams.
ДАЛЬШЕ: Build the invite page with fragment removal, inline login/register, verification/mismatch/error states, and customer project navigation.
ДАЛЬШЕ: Add frontend tests for token-only POST bodies, URL cleanup, auth handoff, acceptance, and navigation.
ДАЛЬШЕ: Update API/security docs and ADR-011 details, validate schema, generate frontend API types (never edit generated types manually).
ДАЛЬШЕ: Run targeted backend/frontend checks, lint/format/typecheck, inspect git diff, and report remaining checks to coordinator.
БЛОКЕРЫ: None; last targeted run passed unavailable-state cases (4 passed).
