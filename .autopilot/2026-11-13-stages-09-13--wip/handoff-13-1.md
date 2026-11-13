СДЕЛАНО: Stage13 начал с durable recovery для Stage09 document processing и Stage11 AI analysis.
СДЕЛАНО: post-commit upload publish failure больше не удаляет сохранённый файл; stale processing lease восстанавливается с generation fencing.
СДЕЛАНО: профильные проверки `apps/ai_assistant/tests apps/documents/tests` прошли: 129 passed.
ФАЙЛЫ: `backend/apps/ai_assistant/{models.py,services.py,tasks.py,migrations/0008_analysis_dispatch_recovery.py,tests/test_analysis_api.py}`.
ФАЙЛЫ: `backend/apps/documents/{models.py,services.py,processing.py,tasks.py,migrations/0006_processing_dispatch_recovery.py,tests/test_processing.py,tests/test_tasks.py}`; `backend/config/settings/base.py`.
ФАЙЛЫ: `docs/ai/AI_ARCHITECTURE.md`, `docs/documents/DOCUMENT_LIFECYCLE.md`, `docs/architecture/SYSTEM_ARCHITECTURE.md`, `docs/operations/LOCAL_DEVELOPMENT.md`, `docs/decisions/ADR-019-Durable-Background-Dispatch-Recovery.md`.
РЕШЕНИЯ: очереди остаются у владельцев доменов; Beat recovery использует row lock, lease и лимит batch 100, без нового cross-domain outbox.
РЕШЕНИЯ: документные сообщения несут ожидаемое поколение; шестьминутная processing lease длиннее Celery hard limit 240 секунд.
РЕШЕНИЯ: текущий код завершает запрос/документ после пяти dispatch reservations даже если все публикации успешны, но worker не успел захватить задачу.
ТУПИКИ: первый post-commit test воспроизвёл реальный дефект: broker exception вызывал outer cleanup и удалял media при уже committed Document row.
ТУПИКИ: существующий Stage11 queue test ожидал немедленный `failed`; обновлён под временный queued статус и bounded retries.
ТУПИКИ: безопасное восстановление PostgreSQL параллельно с CI тестовой БД не запускать; использовать последовательные `docker compose run` проверки.
ДАЛЬШЕ: учесть review замечание: разделить успешные publish count и consecutive broker failures; после пяти успешных publish без claim задача не должна бесконечно/ложно завершаться.
ДАЛЬШЕ: добавить тесты backlog > пяти dispatch leases без worker claim, пяти ошибок broker publish, и доступного retry без ручной DB правки для AI и документов; актуализировать ADR.
ДАЛЬШЕ: затем полный backend/frontend checks, clean scratch PostgreSQL migration, OpenAPI/type parity, секреты/request IDs/REST+WS audit, Compose restart persistence и итоговый verification report; commit/push не выполнять.
