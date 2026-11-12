from celery import shared_task

from apps.documents.services import process_expired_deletions


@shared_task
def process_expired_document_deletions() -> int:
    return process_expired_deletions()
