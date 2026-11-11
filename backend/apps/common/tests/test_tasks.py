from apps.common.tasks import runtime_probe
from config.celery_app import app


def test_runtime_probe_is_repeatable_and_uses_eager_test_mode():
    assert app.conf.task_always_eager
    assert runtime_probe.delay().get() == {"status": "ok"}
    assert runtime_probe.delay().get() == {"status": "ok"}
