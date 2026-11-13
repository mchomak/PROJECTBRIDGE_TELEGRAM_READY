"""Celery worker for asynchronous specification generation."""

import time

from celery import shared_task

from apps.ai_assistant.models import AITask
from apps.ai_assistant.router import generate_text

from .prompts import build_specification_request
from .services import (
    SpecificationGenerationContextTooLargeError,
    claim_generation_request,
    complete_generation_request,
    fail_generation_request,
    generation_request_matches_current_sources,
)

MAX_GENERATION_CONTEXT_BYTES = 24_000
CLAIM_RECOVERY_DELAY_SECONDS = 30
PUBLISH_ATTEMPTS = 3


@shared_task
def recover_stale_specification_generations() -> int:
    """Redispatch durable queued requests missed by an on-commit callback."""
    from .services import recover_stale_specification_generation_dispatches

    return recover_stale_specification_generation_dispatches()


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=None,
    soft_time_limit=240,
    time_limit=300,
)
def generate_specification(self, request_id: str) -> str:
    try:
        state, generation, seconds_left, project_id, context = claim_generation_request(
            request_id=request_id
        )
    except Exception as error:
        raise self.retry(
            exc=error,
            countdown=CLAIM_RECOVERY_DELAY_SECONDS,
        ) from error
    if state == "busy":
        raise self.retry(countdown=max(1, min(60, seconds_left)))
    if state != "claimed":
        return state

    try:
        generation_request = build_specification_request(context)
        input_bytes = len(generation_request.system_prompt.encode("utf-8")) + len(
            generation_request.user_input.encode("utf-8")
        )
        if input_bytes > MAX_GENERATION_CONTEXT_BYTES:
            return _fail_or_retry(
                self,
                request_id=request_id,
                generation=generation,
                error=SpecificationGenerationContextTooLargeError(),
            )
    except Exception as error:
        return _fail_or_retry(
            self,
            request_id=request_id,
            generation=generation,
            error=error,
        )

    try:
        sources_are_current = generation_request_matches_current_sources(
            request_id=request_id,
            generation=generation,
        )
    except Exception as error:
        raise self.retry(
            exc=error,
            countdown=CLAIM_RECOVERY_DELAY_SECONDS,
        ) from error
    if not sources_are_current:
        return "superseded"

    try:
        response = generate_text(
            task_key=AITask.SPECIFICATION_GENERATION,
            project_id=project_id,
            request=generation_request,
        )
    except Exception as error:
        return _fail_or_retry(
            self,
            request_id=request_id,
            generation=generation,
            error=error,
        )

    # Keep the generated body only in memory while retrying a transient publish
    # failure. This avoids repeating a paid provider call when PostgreSQL briefly
    # fails after the model returned. A later Celery delivery still uses the
    # request lease and fencing token if this worker process is lost.
    for attempt in range(PUBLISH_ATTEMPTS):
        try:
            completed = complete_generation_request(
                request_id=request_id,
                generation=generation,
                content=response.text,
            )
            return "succeeded" if completed else "superseded"
        except Exception as error:
            if attempt + 1 == PUBLISH_ATTEMPTS:
                raise self.retry(
                    exc=error,
                    countdown=CLAIM_RECOVERY_DELAY_SECONDS,
                ) from error
            time.sleep(0.1 * (attempt + 1))


def _fail_or_retry(self, *, request_id, generation, error):
    try:
        fail_generation_request(
            request_id=request_id,
            generation=generation,
            error=error,
        )
    except Exception as persistence_error:
        raise self.retry(
            exc=persistence_error,
            countdown=CLAIM_RECOVERY_DELAY_SECONDS,
        ) from persistence_error
    return "failed"
