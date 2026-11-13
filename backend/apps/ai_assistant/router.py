"""Task-keyed AI routing, normalized results, and content-free usage records."""

import hashlib
import json
import math
from dataclasses import dataclass, replace
from datetime import UTC, datetime, time
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection, transaction
from django.db.models import Sum
from django.utils import timezone

from .adapters.openai import OpenAIAdapter, ProviderCallError
from .contracts import (
    RerankedCandidate,
    TextGenerationRequest,
    TextGenerationResponse,
)
from .embedding import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MAX_BATCH_SIZE,
    EMBEDDING_MAX_INPUT_TOKENS_PER_TEXT,
    EMBEDDING_SAFE_REQUEST_BYTES,
    EmbeddingBatch,
    validate_embedding_batch,
)
from .models import (
    AIAnalysisRun,
    AIAnalysisStatus,
    AICapability,
    AIModelProfile,
    AITask,
)
from .providers import get_provider_capabilities


class AIServiceError(Exception):
    """Stable, safe error contract returned to domain services."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class AIProviderUnavailable(AIServiceError):
    def __init__(self, code: str, *, retryable: bool = False, attempt_count: int = 1):
        self.retryable = retryable
        self.attempt_count = attempt_count
        super().__init__(code)


class AICostLimitExceeded(AIServiceError):
    pass


@dataclass(frozen=True)
class _ProviderResult:
    value: object
    input_tokens: int | None
    output_tokens: int | None
    actual_model: str
    attempt_count: int


@dataclass(frozen=True)
class _AttemptUsage:
    profile: AIModelProfile
    reserved_cost: Decimal
    input_tokens: int | None
    output_tokens: int | None
    actual_model: str | None


def _result_with_attempts(result, attempt_count):
    return replace(result, attempt_count=attempt_count)


_ADAPTERS = {"openai": OpenAIAdapter}
_TASK_CAPABILITIES = {
    AITask.MESSAGE_ANALYSIS: AICapability.TEXT_GENERATION,
    AITask.CONVERSATION_ANALYSIS: AICapability.TEXT_GENERATION,
    AITask.CONTRADICTION_DETECTION: AICapability.TEXT_GENERATION,
    AITask.DOCUMENT_EMBEDDING: AICapability.EMBEDDINGS,
    AITask.RAG_RERANKING: AICapability.RERANKING,
    AITask.SPECIFICATION_GENERATION: AICapability.TEXT_GENERATION,
}
_TASK_BUDGET_LOCK_NAMESPACE = 0x50524247
_TASK_BUDGET_LOCK_KEYS = {
    AITask.MESSAGE_ANALYSIS: 1,
    AITask.CONVERSATION_ANALYSIS: 2,
    AITask.CONTRADICTION_DETECTION: 3,
    AITask.DOCUMENT_EMBEDDING: 4,
    AITask.RAG_RERANKING: 5,
    AITask.SPECIFICATION_GENERATION: 6,
}


def _adapter_for(provider_key: str):
    adapter_type = _ADAPTERS.get(provider_key)
    if adapter_type is None:
        raise AIProviderUnavailable("provider_not_supported")
    return adapter_type()


def _resolve_profile(task_key: str, capability: str):
    if task_key not in AITask.values:
        raise AIServiceError("task_not_supported")
    if _TASK_CAPABILITIES[task_key] != capability:
        raise AIServiceError("task_capability_mismatch")
    profile = AIModelProfile.objects.filter(
        task_key=task_key, is_default=True, is_enabled=True
    ).first()
    if profile is None:
        raise AIServiceError("profile_unavailable")
    _validate_profile(profile, capability)
    return profile


def _validate_profile(profile: AIModelProfile, capability: str):
    if capability not in profile.capabilities:
        raise AIServiceError("profile_capability_mismatch")
    declared = get_provider_capabilities(profile.provider_key)
    if declared is None or capability not in declared.capabilities:
        raise AIServiceError("provider_capability_unsupported")
    adapter = _adapter_for(profile.provider_key)
    if capability not in adapter.capabilities:
        raise AIServiceError("provider_capability_unsupported")
    if not profile.model_name:
        raise AIServiceError("profile_model_unconfigured")
    try:
        profile.full_clean()
    except DjangoValidationError:
        raise AIServiceError("profile_configuration_invalid") from None
    if capability == AICapability.EMBEDDINGS and (
        profile.parameters.get("dimensions", EMBEDDING_DIMENSIONS)
        != EMBEDDING_DIMENSIONS
    ):
        raise AIServiceError("embedding_vector_space_incompatible")
    return adapter


def _compatible_fallback(profile, capability):
    fallback = profile.fallback_profile
    if not fallback or not fallback.is_enabled:
        return None
    if fallback.task_key != profile.task_key:
        return None
    try:
        _validate_profile(fallback, capability)
    except AIServiceError:
        return None
    if capability == AICapability.EMBEDDINGS and (
        fallback.provider_key != profile.provider_key
        or fallback.model_name != profile.model_name
        or fallback.parameters.get("dimensions", EMBEDDING_DIMENSIONS)
        != profile.parameters.get("dimensions", EMBEDDING_DIMENSIONS)
        or fallback.embedding_space_key != profile.embedding_space_key
        or fallback.embedding_space_version != profile.embedding_space_version
    ):
        return None
    return fallback


def _decimal_parameter(profile, key, default="0"):
    try:
        value = Decimal(str(profile.parameters.get(key, default)))
    except (InvalidOperation, ValueError):
        raise AIServiceError("profile_cost_configuration_invalid") from None
    if not value.is_finite() or value < 0:
        raise AIServiceError("profile_cost_configuration_invalid")
    return value


def _estimate_cost(profile, *, input_bytes, output_tokens=0):
    input_tokens = input_bytes
    input_rate = _decimal_parameter(profile, "input_usd_per_million_tokens")
    output_rate = _decimal_parameter(profile, "output_usd_per_million_tokens")
    return (
        Decimal(input_tokens) * input_rate + Decimal(output_tokens) * output_rate
    ) / Decimal(1_000_000)


def _calculate_actual_cost(profile, *, input_tokens, output_tokens):
    if input_tokens is None and output_tokens is None:
        return None
    return _estimate_cost(
        profile,
        input_bytes=input_tokens or 0,
        output_tokens=output_tokens or 0,
    )


def _usage_token_count(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def embedding_input_byte_limit(*, task_key=AITask.DOCUMENT_EMBEDDING):
    """Return the active profile cap under OpenAI's conservative request cap."""
    profile = _resolve_profile(task_key, AICapability.EMBEDDINGS)
    configured_limit = int(profile.parameters.get("max_input_bytes", 500_000))
    return min(configured_limit, EMBEDDING_SAFE_REQUEST_BYTES)


def _utc_day_start():
    now = timezone.now().astimezone(UTC)
    return datetime.combine(now.date(), time.min, tzinfo=UTC)


def _lock_task_budget(task_key):
    """Serialize all profile reservations for this task inside PostgreSQL."""
    lock_key = _TASK_BUDGET_LOCK_KEYS.get(task_key)
    if lock_key is None:
        raise AIServiceError("task_not_supported")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            [_TASK_BUDGET_LOCK_NAMESPACE, lock_key],
        )


def _daily_reserved_cost(task_key, day_start, *, exclude_run_id=None):
    runs = AIAnalysisRun.objects.filter(task_key=task_key, started_at__gte=day_start)
    if exclude_run_id is not None:
        runs = runs.exclude(pk=exclude_run_id)
    return runs.aggregate(total=Sum("reserved_cost"))["total"] or Decimal("0")


def _reserve_run(
    *,
    profile,
    task_key,
    project_id,
    prompt_version,
    input_hash,
    input_bytes,
    trigger_type="service",
):
    if project_id is None:
        raise AIServiceError("project_id_required")
    with transaction.atomic():
        _lock_task_budget(task_key)
        locked_profile = AIModelProfile.objects.select_for_update().get(pk=profile.pk)
        try:
            locked_profile.full_clean()
        except DjangoValidationError:
            raise AIServiceError("profile_configuration_invalid") from None
        max_output_tokens = int(locked_profile.parameters.get("max_output_tokens", 0))
        request_cost_limit = _decimal_parameter(
            locked_profile, "max_request_cost_usd", "0.25"
        )
        reservation = _estimate_cost(
            locked_profile, input_bytes=input_bytes, output_tokens=max_output_tokens
        )
        if reservation > request_cost_limit:
            raise AICostLimitExceeded("request_cost_limit_exceeded")
        daily_limit = _decimal_parameter(locked_profile, "daily_budget_usd", "1.00")
        day_start = _utc_day_start()
        already_reserved = _daily_reserved_cost(task_key, day_start)
        if already_reserved + reservation > daily_limit:
            raise AICostLimitExceeded("daily_task_budget_exceeded")
        run = AIAnalysisRun.objects.create(
            project_id=project_id,
            profile=locked_profile,
            task_key=task_key,
            trigger_type=trigger_type,
            provider_key=locked_profile.provider_key,
            model_name=locked_profile.model_name,
            profile_version=locked_profile.config_version,
            prompt_version=prompt_version,
            input_hash=input_hash,
            status=AIAnalysisStatus.RUNNING,
            estimated_cost=reservation,
            reserved_cost=reservation,
            request_budget_limit=request_cost_limit,
            daily_budget_limit=daily_limit,
        )
        run._current_attempt_reservation = reservation
        run._attempt_reservations = [(locked_profile, reservation)]
        run._attempt_usages = []
        return run, locked_profile


def _reserve_additional_attempt(*, run, profile, input_bytes, switch_profile=False):
    with transaction.atomic():
        _lock_task_budget(run.task_key)
        # Keep the call's selected profile snapshot and its rates paired with
        # the adapter invocation, even if an admin edit happens mid-request.
        try:
            profile.full_clean()
        except DjangoValidationError:
            raise AIServiceError("profile_configuration_invalid") from None
        reservation = _estimate_cost(
            profile,
            input_bytes=input_bytes,
            output_tokens=int(profile.parameters.get("max_output_tokens", 0)),
        )
        day_start = _utc_day_start()
        already_reserved = _daily_reserved_cost(
            run.task_key, day_start, exclude_run_id=run.pk
        )
        profile_request_limit = _decimal_parameter(
            profile, "max_request_cost_usd", "0.25"
        )
        request_limit = min(run.request_budget_limit, profile_request_limit)
        if run.reserved_cost + reservation > request_limit:
            code = (
                "fallback_cost_limit_exceeded"
                if switch_profile
                else "request_cost_limit_exceeded"
            )
            raise AICostLimitExceeded(code)
        if already_reserved + run.reserved_cost + reservation > run.daily_budget_limit:
            code = (
                "fallback_cost_limit_exceeded"
                if switch_profile
                else "daily_task_budget_exceeded"
            )
            raise AICostLimitExceeded(code)
        run.reserved_cost += reservation
        run.estimated_cost = max(run.estimated_cost or Decimal("0"), run.reserved_cost)
        run.request_budget_limit = request_limit
        update_fields = [
            "reserved_cost",
            "estimated_cost",
            "request_budget_limit",
        ]
        if switch_profile:
            run.profile = profile
            run.provider_key = profile.provider_key
            run.model_name = profile.model_name
            run.profile_version = profile.config_version
            update_fields.extend(
                ("profile", "provider_key", "model_name", "profile_version")
            )
        run.save(update_fields=update_fields)
        run._current_attempt_reservation = reservation
        run._attempt_reservations.append((profile, reservation))
        return profile


def _switch_run_to_fallback(*, run, profile, input_bytes):
    return _reserve_additional_attempt(
        run=run,
        profile=profile,
        input_bytes=input_bytes,
        switch_profile=True,
    )


def _input_hash(*parts):
    payload = json.dumps(
        parts, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _execute(
    adapter,
    *,
    capability,
    profile,
    invoke,
    run,
    reserve_retry,
    prior_attempt_count=0,
):
    local_attempt_count = 0

    def invoke_attempt():
        nonlocal local_attempt_count
        local_attempt_count += 1
        run.attempt_count = prior_attempt_count + local_attempt_count
        run.save(update_fields=("attempt_count",))

        try:
            value = invoke(adapter, profile)
        except Exception as error:
            usage_source = error
            input_tokens = _usage_token_count(
                getattr(usage_source, "input_tokens", None)
            )
            output_tokens = _usage_token_count(
                getattr(usage_source, "output_tokens", None)
            )
            actual_model = getattr(usage_source, "actual_model", None)
        else:
            usage_source = value if isinstance(value, dict) else {}
            input_tokens = _usage_token_count(usage_source.get("input_tokens"))
            output_tokens = _usage_token_count(usage_source.get("output_tokens"))
            actual_model = usage_source.get("actual_model")

        attempt_index = prior_attempt_count + local_attempt_count - 1
        reservations = getattr(run, "_attempt_reservations", ())
        if attempt_index < len(reservations):
            attempt_profile, attempt_reservation = reservations[attempt_index]
        else:
            attempt_profile = profile
            attempt_reservation = getattr(
                run, "_current_attempt_reservation", Decimal("0")
            )
        run._attempt_usages.append(
            _AttemptUsage(
                profile=attempt_profile,
                reserved_cost=attempt_reservation,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                actual_model=(
                    actual_model
                    if isinstance(actual_model, str) and actual_model
                    else attempt_profile.model_name
                ),
            )
        )
        if "value" in locals():
            return value
        raise usage_source

    try:
        value = invoke_attempt()
        return _ProviderResult(
            value=value,
            input_tokens=value.get("input_tokens"),
            output_tokens=value.get("output_tokens"),
            actual_model=value.get("actual_model") or profile.model_name,
            attempt_count=local_attempt_count,
        )
    except ProviderCallError as error:
        if not error.retryable:
            raise AIProviderUnavailable(
                error.code, attempt_count=local_attempt_count
            ) from None
        # One bounded retry for rate limits, transient HTTP errors, and timeouts.
        reserve_retry()
        try:
            value = invoke_attempt()
            return _ProviderResult(
                value=value,
                input_tokens=value.get("input_tokens"),
                output_tokens=value.get("output_tokens"),
                actual_model=value.get("actual_model") or profile.model_name,
                attempt_count=local_attempt_count,
            )
        except ProviderCallError as retry_error:
            raise AIProviderUnavailable(
                retry_error.code,
                retryable=True,
                attempt_count=local_attempt_count,
            ) from None


def _run_fallback(
    *, profile, capability, invoke, run, input_bytes, prior_attempt_count
):
    fallback = _compatible_fallback(profile, capability)
    if fallback is None:
        return None
    fallback = _switch_run_to_fallback(
        run=run, profile=fallback, input_bytes=input_bytes
    )
    adapter = _validate_profile(fallback, capability)
    try:
        result = _execute(
            adapter,
            capability=capability,
            profile=fallback,
            invoke=invoke,
            run=run,
            prior_attempt_count=prior_attempt_count,
            reserve_retry=lambda: _reserve_additional_attempt(
                run=run, profile=fallback, input_bytes=input_bytes
            ),
        )
    except AIProviderUnavailable as error:
        raise AIProviderUnavailable(
            error.code,
            retryable=error.retryable,
            attempt_count=prior_attempt_count + error.attempt_count,
        ) from None
    return fallback, result


def _finish_run(run, *, profile, result=None, error_code=""):
    run.status = (
        AIAnalysisStatus.SUCCEEDED
        if result is not None and not error_code
        else AIAnalysisStatus.FAILED
    )
    run.error_code = error_code
    run.attempt_count = max(
        run.attempt_count, result.attempt_count if result is not None else 1
    )
    attempt_usages = list(getattr(run, "_attempt_usages", ()))
    if not attempt_usages and result is not None:
        attempt_reservation = getattr(run, "_current_attempt_reservation", Decimal("0"))
        attempt_usages.append(
            _AttemptUsage(
                profile=profile,
                reserved_cost=attempt_reservation,
                input_tokens=_usage_token_count(result.input_tokens),
                output_tokens=_usage_token_count(result.output_tokens),
                actual_model=result.actual_model,
            )
        )

    if attempt_usages:
        adjusted_total = Decimal("0")
        total_input_tokens = 0
        total_output_tokens = 0
        has_input_tokens = False
        has_output_tokens = False
        for attempt in attempt_usages:
            actual_cost = _calculate_actual_cost(
                attempt.profile,
                input_tokens=attempt.input_tokens,
                output_tokens=attempt.output_tokens,
            )
            adjusted_total += max(
                attempt.reserved_cost,
                actual_cost if actual_cost is not None else Decimal("0"),
            )
            if attempt.input_tokens is not None:
                total_input_tokens += attempt.input_tokens
                has_input_tokens = True
            if attempt.output_tokens is not None:
                total_output_tokens += attempt.output_tokens
                has_output_tokens = True
        run.reserved_cost = max(run.reserved_cost, adjusted_total)
        run.estimated_cost = max(
            run.estimated_cost or Decimal("0"),
            run.reserved_cost,
            adjusted_total,
        )
        run.input_tokens = total_input_tokens if has_input_tokens else None
        run.output_tokens = total_output_tokens if has_output_tokens else None
        run.model_name = next(
            (
                attempt.actual_model
                for attempt in reversed(attempt_usages)
                if attempt.actual_model
            ),
            run.model_name,
        )
    elif result is not None:
        run.model_name = result.actual_model
        run.input_tokens = result.input_tokens
        run.output_tokens = result.output_tokens
    run.completed_at = timezone.now()
    with transaction.atomic():
        _lock_task_budget(run.task_key)
        run.save(
            update_fields=(
                "status",
                "error_code",
                "attempt_count",
                "model_name",
                "input_tokens",
                "output_tokens",
                "estimated_cost",
                "reserved_cost",
                "completed_at",
            )
        )


def generate_text(
    *, task_key: str, project_id, request: TextGenerationRequest, trigger_type="service"
) -> TextGenerationResponse:
    if not isinstance(request, TextGenerationRequest):
        raise AIServiceError("generation_request_invalid")
    if not request.system_prompt.strip() or not request.user_input.strip():
        raise AIServiceError("generation_input_empty")
    if not request.prompt_version or len(request.prompt_version) > 64:
        raise AIServiceError("prompt_version_invalid")
    profile = _resolve_profile(task_key, AICapability.TEXT_GENERATION)
    max_bytes = int(profile.parameters.get("max_input_bytes", 32_000))
    input_bytes = len(request.system_prompt.encode()) + len(request.user_input.encode())
    if input_bytes > max_bytes:
        raise AICostLimitExceeded("input_size_limit_exceeded")
    max_output = int(profile.parameters.get("max_output_tokens", 1024))
    if max_output < 1 or max_output > 8192:
        raise AIServiceError("profile_output_limit_invalid")

    run, profile = _reserve_run(
        profile=profile,
        task_key=task_key,
        project_id=project_id,
        prompt_version=request.prompt_version,
        input_hash=_input_hash(request.system_prompt, request.user_input),
        input_bytes=input_bytes,
        trigger_type=trigger_type,
    )
    adapter = _validate_profile(profile, AICapability.TEXT_GENERATION)
    invoke = lambda provider, chosen: provider.generate(  # noqa: E731
        profile=chosen, request=request
    )
    result = None
    used_profile = profile
    try:
        try:
            result = _execute(
                adapter,
                capability=AICapability.TEXT_GENERATION,
                profile=profile,
                invoke=invoke,
                run=run,
                reserve_retry=lambda: _reserve_additional_attempt(
                    run=run, profile=profile, input_bytes=input_bytes
                ),
            )
            used_profile = profile
        except AIProviderUnavailable as primary_error:
            if not primary_error.retryable:
                raise
            run.attempt_count = primary_error.attempt_count
            run.save(update_fields=("attempt_count",))
            fallback_result = _run_fallback(
                profile=profile,
                capability=AICapability.TEXT_GENERATION,
                invoke=invoke,
                run=run,
                input_bytes=input_bytes,
                prior_attempt_count=primary_error.attempt_count,
            )
            if fallback_result is None:
                raise primary_error
            used_profile, result = fallback_result
            result = _result_with_attempts(
                result, primary_error.attempt_count + result.attempt_count
            )

        parsed = None
        if request.response_schema is not None:
            try:
                parsed = json.loads(result.value["text"])
            except (TypeError, ValueError, KeyError):
                raise AIProviderUnavailable("provider_response_invalid") from None
        _finish_run(run, profile=used_profile, result=result)
        return TextGenerationResponse(
            text=result.value["text"],
            parsed=parsed,
            provider_key=used_profile.provider_key,
            model_name=result.actual_model,
            profile_key=used_profile.profile_key,
            profile_version=used_profile.config_version,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost=str(run.estimated_cost) if run.estimated_cost else None,
        )
    except AIServiceError as error:
        if isinstance(error, AIProviderUnavailable):
            run.attempt_count = max(run.attempt_count, error.attempt_count)
        _finish_run(
            run,
            profile=used_profile if result is not None else profile,
            result=result,
            error_code=error.code,
        )
        raise
    except Exception:
        _finish_run(
            run,
            profile=used_profile if result is not None else profile,
            result=result,
            error_code="provider_response_invalid",
        )
        raise AIProviderUnavailable("provider_response_invalid") from None


def embed_texts(texts, *, task_key="document_embedding", project_id=None):
    if (
        not isinstance(texts, list)
        or not texts
        or len(texts) > EMBEDDING_MAX_BATCH_SIZE
    ):
        raise AIServiceError("embedding_batch_invalid")
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise AIServiceError("embedding_input_invalid")
    profile = _resolve_profile(task_key, AICapability.EMBEDDINGS)
    text_bytes = [len(text.encode("utf-8")) for text in texts]
    input_bytes = sum(text_bytes)
    max_input_bytes = min(
        int(profile.parameters.get("max_input_bytes", 500_000)),
        EMBEDDING_SAFE_REQUEST_BYTES,
    )
    if (
        any(size > EMBEDDING_MAX_INPUT_TOKENS_PER_TEXT for size in text_bytes)
        or input_bytes > max_input_bytes
    ):
        raise AICostLimitExceeded("input_size_limit_exceeded")
    run, profile = _reserve_run(
        profile=profile,
        task_key=task_key,
        project_id=project_id,
        prompt_version="",
        input_hash=_input_hash(*texts),
        input_bytes=input_bytes,
    )
    adapter = _validate_profile(profile, AICapability.EMBEDDINGS)
    invoke = lambda provider, chosen: provider.embed(  # noqa: E731
        profile=chosen, texts=texts
    )
    result = None
    used_profile = profile
    try:
        try:
            result = _execute(
                adapter,
                capability=AICapability.EMBEDDINGS,
                profile=profile,
                invoke=invoke,
                run=run,
                reserve_retry=lambda: _reserve_additional_attempt(
                    run=run, profile=profile, input_bytes=input_bytes
                ),
            )
            used_profile = profile
        except AIProviderUnavailable as primary_error:
            if not primary_error.retryable:
                raise
            run.attempt_count = primary_error.attempt_count
            run.save(update_fields=("attempt_count",))
            fallback_result = _run_fallback(
                profile=profile,
                capability=AICapability.EMBEDDINGS,
                invoke=invoke,
                run=run,
                input_bytes=input_bytes,
                prior_attempt_count=primary_error.attempt_count,
            )
            if fallback_result is None:
                raise primary_error
            used_profile, result = fallback_result
            result = _result_with_attempts(
                result, primary_error.attempt_count + result.attempt_count
            )
        batch = EmbeddingBatch(
            vectors=result.value["vectors"],
            profile_key=used_profile.embedding_space_key,
            profile_version=used_profile.embedding_space_version,
            model_name=result.actual_model,
        )
        validate_embedding_batch(batch, expected_count=len(texts))
        _finish_run(run, profile=used_profile, result=result)
        return batch
    except ProviderCallError as error:
        _finish_run(run, profile=profile, error_code=error.code)
        raise AIProviderUnavailable(error.code) from None
    except AIServiceError as error:
        _finish_run(
            run,
            profile=used_profile if result is not None else profile,
            result=result,
            error_code=error.code,
        )
        raise
    except Exception:
        _finish_run(
            run,
            profile=used_profile if result is not None else profile,
            result=result,
            error_code="provider_response_invalid",
        )
        raise AIProviderUnavailable("provider_response_invalid") from None


def rerank_candidates(*, task_key, project_id, query, candidates):
    """Score candidates with a configured structured-output reranker."""
    if not isinstance(query, str) or not query.strip():
        raise AIServiceError("rerank_query_invalid")
    if (
        not isinstance(candidates, list)
        or not candidates
        or any(not isinstance(item, str) or not item.strip() for item in candidates)
    ):
        raise AIServiceError("rerank_candidates_invalid")
    profile = _resolve_profile(task_key, AICapability.RERANKING)
    max_candidates = int(profile.parameters.get("max_candidates", 100))
    if max_candidates < 1 or max_candidates > 100:
        raise AIServiceError("profile_candidate_limit_invalid")
    if len(candidates) > max_candidates:
        raise AICostLimitExceeded("candidate_count_limit_exceeded")
    input_bytes = len(query.encode("utf-8")) + sum(
        len(candidate.encode("utf-8")) for candidate in candidates
    )
    if len(query.encode("utf-8")) > 8192 or input_bytes > int(
        profile.parameters.get("max_input_bytes", 32_000)
    ):
        raise AICostLimitExceeded("input_size_limit_exceeded")
    max_output_tokens = int(profile.parameters.get("max_output_tokens", 4096))
    if max_output_tokens < 1 or max_output_tokens > 8192:
        raise AIServiceError("profile_output_limit_invalid")

    run, profile = _reserve_run(
        profile=profile,
        task_key=task_key,
        project_id=project_id,
        prompt_version="rag-reranking-v1",
        input_hash=_input_hash(query, *candidates),
        input_bytes=input_bytes,
        trigger_type="retrieval",
    )
    adapter = _validate_profile(profile, AICapability.RERANKING)
    invoke = lambda provider, chosen: provider.rerank(  # noqa: E731
        profile=chosen, query=query, candidates=candidates
    )
    result = None
    used_profile = profile
    try:
        try:
            result = _execute(
                adapter,
                capability=AICapability.RERANKING,
                profile=profile,
                invoke=invoke,
                run=run,
                reserve_retry=lambda: _reserve_additional_attempt(
                    run=run, profile=profile, input_bytes=input_bytes
                ),
            )
            used_profile = profile
        except AIProviderUnavailable as primary_error:
            if not primary_error.retryable:
                raise
            run.attempt_count = primary_error.attempt_count
            run.save(update_fields=("attempt_count",))
            fallback_result = _run_fallback(
                profile=profile,
                capability=AICapability.RERANKING,
                invoke=invoke,
                run=run,
                input_bytes=input_bytes,
                prior_attempt_count=primary_error.attempt_count,
            )
            if fallback_result is None:
                raise primary_error
            used_profile, result = fallback_result
            result = _result_with_attempts(
                result, primary_error.attempt_count + result.attempt_count
            )

        raw_candidates = (
            result.value.get("ranked_candidates")
            if isinstance(result.value, dict)
            else None
        )
        if not isinstance(raw_candidates, list) or len(raw_candidates) != len(
            candidates
        ):
            raise AIProviderUnavailable("provider_response_invalid")
        normalized = []
        seen = set()
        for item in raw_candidates:
            if not isinstance(item, dict):
                raise AIProviderUnavailable("provider_response_invalid")
            index = item.get("index")
            score = item.get("score")
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(candidates)
                or index in seen
                or isinstance(score, bool)
                or not isinstance(score, int | float)
                or not math.isfinite(score)
                or not 0 <= score <= 1
            ):
                raise AIProviderUnavailable("provider_response_invalid")
            seen.add(index)
            normalized.append(RerankedCandidate(index=index, score=float(score)))
        if seen != set(range(len(candidates))):
            raise AIProviderUnavailable("provider_response_invalid")
        normalized.sort(key=lambda item: (-item.score, item.index))
        _finish_run(run, profile=used_profile, result=result)
        return normalized
    except AIServiceError as error:
        if isinstance(error, AIProviderUnavailable):
            run.attempt_count = max(run.attempt_count, error.attempt_count)
        _finish_run(
            run,
            profile=used_profile if result is not None else profile,
            result=result,
            error_code=error.code,
        )
        raise
    except Exception:
        _finish_run(
            run,
            profile=used_profile if result is not None else profile,
            result=result,
            error_code="provider_response_invalid",
        )
        raise AIProviderUnavailable("provider_response_invalid") from None
