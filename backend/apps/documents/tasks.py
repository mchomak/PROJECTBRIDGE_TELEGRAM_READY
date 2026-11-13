from celery import shared_task

from apps.documents.processing import process_document
from apps.documents.services import process_expired_deletions


@shared_task
def process_expired_document_deletions() -> int:
    return process_expired_deletions()


@shared_task(
    acks_late=True, reject_on_worker_lost=True, soft_time_limit=180, time_limit=240
)
def process_project_document(document_id: str) -> str | None:
    document = process_document(document_id=document_id)
    return document.processing_status if document is not None else None
