СДЕЛАНО: R01–R04 account model, email normalization, password hashing, and service behavior are implemented and covered.
СДЕЛАНО: R11–R14 verification tokens use 256-bit entropy, SHA-256 digests, 24-hour expiry, rotation, and single-use confirmation.
СДЕЛАНО: common DRF/CSRF error envelopes and separate core/verification URL modules are in place.
СДЕЛАНО: Redis cache/throttle, local frontend URL, and production cookie defaults are configured.
СДЕЛАНО: DATA_MODEL and ADR 0005 document the additive migration strategy; all backend checks passed.
ФАЙЛЫ: backend/apps/accounts/models.py; backend/apps/accounts/services.py; backend/apps/accounts/migrations/0001_initial.py; backend/apps/accounts/tests/test_models.py.
ФАЙЛЫ: backend/apps/accounts/api/__init__.py; backend/apps/accounts/api/urls.py; backend/apps/accounts/api/core_urls.py; backend/apps/accounts/api/verification_urls.py; backend/apps/common/api/__init__.py; backend/apps/common/api/errors.py.
ФАЙЛЫ: backend/apps/common/tests/test_api_errors.py; backend/config/settings/base.py; backend/config/settings/local.py; backend/config/settings/production.py; backend/config/settings/test.py; backend/config/urls.py.
ФАЙЛЫ: backend/config/tests/test_production_settings.py; backend/config/tests/test_auth_url_scaffolding.py; backend/requirements.txt; .env.example; docker-compose.yml.
ФАЙЛЫ: docs/database/DATA_MODEL.md; docs/adr/0005-additive-accounts-user-migration.md.
РЕШЕНИЯ: Existing database keeps its unchanged empty auth_user table; clean databases configured with accounts.User before migration do not create auth_user.
РЕШЕНИЯ: Email normalization trims then casefolds the full address; Argon2 is preferred and PBKDF2 remains for compatible hashes.
ТУПИКИ: Compose run uses an immutable image; rebuild it after workspace edits so focused tests see new files.
ТУПИКИ: The initial Argon2 probe had PowerShell quoting and hash-prefix mistakes; the corrected Python 3.13.18 round-trip passed.
ДАЛЬШЕ: Backend suite is 27 passed (baseline 20); Ruff, makemigrations, empty/current database checks, and Compose URL check passed; no blockers.
