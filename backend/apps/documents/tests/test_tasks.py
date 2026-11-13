from django.conf import settings


def test_celery_beat_schedules_document_deletion_sweep_every_five_minutes():
    sweep = settings.CELERY_BEAT_SCHEDULE["document-lifecycle-deletion-sweep"]

    assert sweep == {
        "task": "apps.documents.tasks.process_expired_document_deletions",
        "schedule": 300.0,
    }


def test_celery_task_returns_the_service_sweep_result(monkeypatch):
    from apps.documents import tasks

    monkeypatch.setattr(tasks, "process_expired_deletions", lambda: 2)

    assert tasks.process_expired_document_deletions.run() == 2


def test_celery_beat_schedules_processing_recovery_every_minute():
    recovery = settings.CELERY_BEAT_SCHEDULE["document-processing-dispatch-recovery"]

    assert recovery == {
        "task": "apps.documents.tasks.recover_stale_document_processing_task",
        "schedule": 60.0,
    }


def test_recovery_task_returns_the_service_result(monkeypatch):
    from apps.documents import tasks

    monkeypatch.setattr(tasks, "recover_stale_document_processing", lambda: 3)

    assert tasks.recover_stale_document_processing_task.run() == 3
