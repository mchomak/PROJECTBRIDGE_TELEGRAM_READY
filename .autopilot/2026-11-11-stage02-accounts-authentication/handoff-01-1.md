СДЕЛАНО: R01 модель, UUID/email manager, initial accounts migration; focused migration-backed tests passed.
СДЕЛАНО: R02 normalization and duplicate rejection; registration and authentication service seams implemented.
СДЕЛАНО: R11–R14 token model/service rotation, digest storage, 24-hour expiry, single-use confirmation; focused tests passed.
ФАЙЛЫ: backend/apps/accounts/models.py, backend/apps/accounts/services.py, backend/apps/accounts/migrations/0001_initial.py.
ФАЙЛЫ: backend/apps/accounts/tests/test_models.py, backend/config/settings/base.py, backend/config/settings/local.py.
ФАЙЛЫ: backend/config/settings/production.py, backend/config/settings/test.py, backend/requirements.txt.
РЕШЕНИЯ: `AUTH_USER_MODEL` is `accounts.User`; Python package remains `apps.accounts` and legacy auth tables are untouched.
РЕШЕНИЯ: Email normalization trims then casefolds the full address; Argon2 25.1.0 is pinned and configured before PBKDF2.
РЕШЕНИЯ: Verification links use `/verify-email#token=...`; raw tokens are returned only through local email delivery.
ТУПИКИ: The initial supplied test expected `apps.accounts.User`; corrected to the authoritative app label `accounts.User`.
ТУПИКИ: Test commands run inside `/app`; use `apps/accounts/tests/test_models.py`, not `backend/apps/accounts/tests/test_models.py`.
ТУПИКИ: The late build/test command raced the image rebuild and tested a stale image; its missing-service failure is inconclusive.
ДАЛЬШЕ: Await `docker compose build backend`; rerun the focused file and assert Argon2 hashes verify in Python 3.13.
ДАЛЬШЕ: Add common DRF/CSRF errors, auth URL modules, Redis/cache/throttle and cookie/env wiring; update DATA_MODEL and add ADR.
ДАЛЬШЕ: Run makemigrations check, clean and current PostgreSQL migration checks, then the full backend suite; report exact counts.
