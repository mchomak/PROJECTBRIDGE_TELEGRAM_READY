"""Celery entry points for manual project analysis."""

from celery import shared_task

from .analysis import run_project_analysis
from .services import (
    claim_analysis_request,
    complete_analysis_request,
    fail_analysis_request,
    recover_stale_analysis_dispatches,
)


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=None,
    soft_time_limit=240,
    time_limit=300,
)
def analyze_project(self, request_id: str) -> str:
    """Claim a durable request or reschedule until its execution lease expires."""
    state, generation, seconds_left = claim_analysis_request(request_id=request_id)
    if state == "busy":
        raise self.retry(countdown=max(1, min(60, seconds_left)))
    if state != "claimed":
        return state

    try:
        result = run_project_analysis(
            request_id=request_id,
            generation=generation,
        )
        if result is None:
            return "superseded"
        response, proposals, evidence_by_key = result
        completed = complete_analysis_request(
            request_id=request_id,
            generation=generation,
            response=response,
            proposals=proposals,
            evidence_by_key=evidence_by_key,
        )
        return "succeeded" if completed else "superseded"
    except Exception as error:
        fail_analysis_request(
            request_id=request_id,
            generation=generation,
            error=error,
        )
        return "failed"


@shared_task
def recover_stale_analysis_dispatches_task() -> int:
    return recover_stale_analysis_dispatches()
