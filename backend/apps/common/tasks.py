from celery import shared_task


@shared_task
def runtime_probe() -> dict[str, str]:
    return {"status": "ok"}
