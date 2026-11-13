import hashlib
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.test import override_settings

from apps.accounts.models import User
from apps.ai_assistant import router
from apps.ai_assistant.adapters import openai as openai_adapter
from apps.ai_assistant.adapters.openai import (
    OpenAIAdapter,
    ProviderCallError,
)
from apps.ai_assistant.contracts import TextGenerationRequest
from apps.ai_assistant.embedding import EmbeddingServiceUnavailable
from apps.ai_assistant.models import (
    AIAnalysisRun,
    AICapability,
    AIModelProfile,
    AITask,
)
from apps.projects.models import Project, ProjectType


@pytest.fixture(autouse=True)
def clear_seed_profiles(db):
    AIModelProfile.objects.all().update(fallback_profile=None)
    AIModelProfile.objects.all().delete()


@pytest.fixture
def project(db):
    user = User.objects.create_user(email="ai-router@example.com")
    return Project.objects.create(
        name="Router test",
        project_type=ProjectType.WEBSITE,
        created_by=user,
    )


def _cost_parameters(**overrides):
    return {
        "input_usd_per_million_tokens": "0.10",
        "output_usd_per_million_tokens": "0.50",
        "max_input_bytes": 32000,
        "max_output_tokens": 100,
        "max_request_cost_usd": "1.00",
        "daily_budget_usd": "2.00",
        "timeout_seconds": 30,
        "max_candidates": 100,
        **overrides,
    }


def _profile(*, task=AITask.MESSAGE_ANALYSIS, **overrides):
    fields = {
        "profile_key": f"{task}-primary",
        "task_key": task,
        "provider_key": "openai",
        "model_name": "gpt-6-luna",
        "capabilities": [AICapability.TEXT_GENERATION],
        "parameters": _cost_parameters(),
        "is_default": True,
        "is_enabled": True,
    }
    fields.update(overrides)
    return AIModelProfile.objects.create(**fields)


class _FakeAdapter:
    capabilities = frozenset(
        {
            AICapability.TEXT_GENERATION,
            AICapability.EMBEDDINGS,
            AICapability.RERANKING,
        }
    )
    calls = 0

    def generate(self, *, profile, request):
        self.calls += 1
        if getattr(type(self), "failures_remaining", 0):
            type(self).failures_remaining -= 1
            raise ProviderCallError("provider_rate_limited", retryable=True)
        return {
            "text": '{"ok":true}',
            "input_tokens": 20,
            "output_tokens": 4,
            "actual_model": profile.model_name,
        }

    def embed(self, *, profile, texts):
        return {
            "vectors": [[1.0, *([0.0] * 1535)] for _ in texts],
            "input_tokens": len(texts) * 3,
            "actual_model": profile.model_name,
        }

    def rerank(self, *, profile, query, candidates):
        return {
            "ranked_candidates": [
                {"index": index, "score": index / len(candidates)}
                for index in range(len(candidates))
            ],
            "input_tokens": 18,
            "output_tokens": 7,
            "actual_model": profile.model_name,
        }


@pytest.mark.django_db
def test_router_records_content_free_usage_and_structured_output(monkeypatch, project):
    _profile(
        parameters=_cost_parameters(
            input_usd_per_million_tokens="2.00",
            output_usd_per_million_tokens="10.00",
        )
    )
    monkeypatch.setattr(router, "_ADAPTERS", {"openai": _FakeAdapter})

    result = router.generate_text(
        task_key=AITask.MESSAGE_ANALYSIS,
        project_id=project.pk,
        request=TextGenerationRequest(
            system_prompt="Return JSON.",
            user_input="Summarize this requirement.",
            prompt_version="message-analysis-v1",
            response_schema={
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
                "additionalProperties": False,
            },
        ),
    )

    run = AIAnalysisRun.objects.get()
    assert result.parsed == {"ok": True}
    assert result.profile_key == "message_analysis-primary"
    assert result.profile_version == 1
    assert run.status == "succeeded"
    assert (
        run.input_hash
        == hashlib.sha256(b'["Return JSON.","Summarize this requirement."]').hexdigest()
    )
    assert run.input_tokens == 20
    assert run.output_tokens == 4
    assert str(run.estimated_cost) == "0.00107800"
    assert str(run.reserved_cost) == "0.00107800"
    assert not hasattr(run, "prompt")
    assert not hasattr(run, "input_text")


@pytest.mark.django_db
def test_profile_selection_is_task_scoped_and_missing_credentials_are_normalized(
    monkeypatch, project
):
    _profile()
    with pytest.raises(router.AIServiceError, match="profile_unavailable"):
        router.generate_text(
            task_key=AITask.CONVERSATION_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    with pytest.raises(EmbeddingServiceUnavailable):
        with override_settings(AI_EMBEDDING_SERVICE=""):
            from apps.ai_assistant.embedding import embed_texts

            embed_texts(["text"], project_id=project.pk)


@pytest.mark.django_db
def test_profile_rejects_provider_capability_mismatch():
    profile = AIModelProfile(
        profile_key="reranker",
        task_key=AITask.RAG_RERANKING,
        provider_key="unsupported-provider",
        model_name="gpt-6-luna",
        capabilities=[AICapability.RERANKING],
        parameters={},
        is_default=True,
        is_enabled=True,
    )

    with pytest.raises(ValidationError, match="Provider does not support"):
        profile.full_clean()


@pytest.mark.django_db
def test_profile_configuration_changes_increment_version():
    profile = _profile()

    profile.parameters = _cost_parameters(max_output_tokens=300)
    profile.save()

    profile.refresh_from_db()
    assert profile.config_version == 2


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("timeout_seconds", 29),
        ("timeout_seconds", 61),
        ("timeout_seconds", "30"),
        ("max_input_bytes", True),
        ("max_input_bytes", 20 * 1024 * 1024 + 1),
        ("max_output_tokens", "100"),
        ("max_output_tokens", 8193),
        ("max_request_cost_usd", "NaN"),
        ("daily_budget_usd", "-0.1"),
        ("input_usd_per_million_tokens", "invalid"),
        ("reasoning_effort", "xhigh"),
    ],
)
@pytest.mark.django_db
def test_profile_security_and_cost_limits_are_validated_on_save(parameter, value):
    with pytest.raises(ValidationError):
        _profile(parameters=_cost_parameters(**{parameter: value}))


@pytest.mark.django_db
def test_invalid_timeout_is_rejected_on_save_and_before_provider_execution(
    monkeypatch, project
):
    with pytest.raises(ValidationError, match="timeout_seconds"):
        _profile(parameters=_cost_parameters(timeout_seconds=61))

    profile = _profile()
    invalid_parameters = {**profile.parameters, "timeout_seconds": 61}
    AIModelProfile.objects.filter(pk=profile.pk).update(parameters=invalid_parameters)
    fake = _FakeAdapter()
    monkeypatch.setattr(router, "_adapter_for", lambda provider: fake)

    with pytest.raises(router.AIServiceError, match="profile_configuration_invalid"):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    assert fake.calls == 0
    assert not AIAnalysisRun.objects.exists()


@pytest.mark.django_db
def test_invalid_cost_configuration_bypassing_save_is_rejected_before_call(
    monkeypatch, project
):
    profile = _profile()
    invalid_parameters = {**profile.parameters, "max_request_cost_usd": "NaN"}
    AIModelProfile.objects.filter(pk=profile.pk).update(parameters=invalid_parameters)
    fake = _FakeAdapter()
    monkeypatch.setattr(router, "_adapter_for", lambda provider: fake)

    with pytest.raises(router.AIServiceError, match="profile_configuration_invalid"):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    assert fake.calls == 0
    assert not AIAnalysisRun.objects.exists()


@pytest.mark.django_db
def test_compatible_fallback_runs_after_one_bounded_retry(monkeypatch, project):
    _profile()
    fallback = _profile(
        profile_key="message-analysis-fallback",
        model_name="gpt-6.1-sol",
        is_default=False,
        parameters=_cost_parameters(
            input_usd_per_million_tokens="2.00",
            output_usd_per_million_tokens="10.00",
        ),
    )
    primary = AIModelProfile.objects.get(profile_key="message_analysis-primary")
    primary.fallback_profile = fallback
    primary.save()
    monkeypatch.setattr(router, "_ADAPTERS", {"openai": _FakeAdapter})
    _FakeAdapter.failures_remaining = 2
    _FakeAdapter.calls = 0

    result = router.generate_text(
        task_key=AITask.MESSAGE_ANALYSIS,
        project_id=project.pk,
        request=TextGenerationRequest("system", "content", "v1"),
    )

    run = AIAnalysisRun.objects.get()
    assert result.profile_key == "message-analysis-fallback"
    assert result.model_name == "gpt-6.1-sol"
    assert run.profile_id == fallback.pk
    assert run.attempt_count == 3
    assert str(run.reserved_cost) == "0.00112860"
    assert str(run.estimated_cost) == "0.00112860"


@pytest.mark.django_db
def test_cost_guard_rejects_before_provider_execution(monkeypatch, project):
    _profile(parameters=_cost_parameters(max_request_cost_usd="0.00001"))
    fake = _FakeAdapter()
    monkeypatch.setattr(router, "_adapter_for", lambda provider: fake)

    with pytest.raises(router.AICostLimitExceeded, match="request_cost_limit"):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    assert fake.calls == 0
    assert not AIAnalysisRun.objects.exists()


@pytest.mark.django_db
def test_retry_attempt_is_reserved_before_retry_adapter_call(monkeypatch, project):
    _profile(parameters=_cost_parameters(max_request_cost_usd="0.00006"))
    fake = _FakeAdapter()
    fake.calls = 0
    _FakeAdapter.failures_remaining = 1
    monkeypatch.setattr(router, "_adapter_for", lambda provider: fake)

    with pytest.raises(router.AICostLimitExceeded, match="request_cost_limit"):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    run = AIAnalysisRun.objects.get()
    assert fake.calls == 1
    assert run.status == "failed"
    assert run.attempt_count == 1
    assert str(run.reserved_cost) == "0.00005130"
    assert str(run.estimated_cost) == "0.00005130"


@pytest.mark.django_db
def test_successful_retry_keeps_all_attempt_reservations_and_usage_overrun(
    monkeypatch, project
):
    _profile()

    class OverrunAfterRetryAdapter(_FakeAdapter):
        def generate(self, *, profile, request):
            self.calls += 1
            if self.calls == 1:
                raise ProviderCallError("provider_rate_limited", retryable=True)
            return {
                "text": "done",
                "input_tokens": 1_000_000,
                "output_tokens": 200,
                "actual_model": profile.model_name,
            }

    fake = OverrunAfterRetryAdapter()
    monkeypatch.setattr(router, "_adapter_for", lambda provider: fake)
    result = router.generate_text(
        task_key=AITask.MESSAGE_ANALYSIS,
        project_id=project.pk,
        request=TextGenerationRequest("system", "content", "v1"),
    )

    run = AIAnalysisRun.objects.get()
    assert result.text == "done"
    assert run.attempt_count == 2
    assert run.reserved_cost > router._estimate_cost(
        run.profile, input_bytes=13, output_tokens=100
    )
    assert run.estimated_cost == run.reserved_cost
    assert run.reserved_cost >= router._calculate_actual_cost(
        run.profile,
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
    )


@pytest.mark.django_db
def test_retry_reservation_uses_the_same_profile_snapshot_as_adapter_call(
    monkeypatch, project
):
    primary = _profile(parameters=_cost_parameters(max_request_cost_usd="0.00015"))

    class ProfileChangingAdapter:
        capabilities = _FakeAdapter.capabilities

        def __init__(self):
            self.calls = 0
            self.configs = []

        def generate(self, *, profile, request):
            self.calls += 1
            self.configs.append(
                (
                    profile.config_version,
                    profile.parameters["input_usd_per_million_tokens"],
                    profile.parameters["max_output_tokens"],
                )
            )
            if self.calls == 1:
                edited = AIModelProfile.objects.get(pk=primary.pk)
                edited.parameters = _cost_parameters(
                    input_usd_per_million_tokens="10000.00",
                    output_usd_per_million_tokens="10000.00",
                    max_output_tokens=8192,
                    max_request_cost_usd="100.00",
                )
                edited.save()
                raise ProviderCallError("provider_rate_limited", retryable=True)
            return {
                "text": "done",
                "input_tokens": 20,
                "output_tokens": 4,
                "actual_model": profile.model_name,
            }

    adapter = ProfileChangingAdapter()
    monkeypatch.setattr(router, "_adapter_for", lambda _provider: adapter)

    response = router.generate_text(
        task_key=AITask.MESSAGE_ANALYSIS,
        project_id=project.pk,
        request=TextGenerationRequest("system", "content", "v1"),
    )

    run = AIAnalysisRun.objects.get()
    assert response.text == "done"
    assert adapter.calls == 2
    assert adapter.configs == [(1, "0.10", 100), (1, "0.10", 100)]
    assert primary.config_version == 1
    assert AIModelProfile.objects.get(pk=primary.pk).config_version == 2
    assert str(run.reserved_cost) == "0.00010260"
    assert run.profile_version == 1


@pytest.mark.django_db
def test_malformed_structured_generation_retains_billable_usage(monkeypatch, project):
    _profile()

    class MalformedGenerationAdapter(_FakeAdapter):
        def generate(self, *, profile, request):
            return {
                "text": "not-json",
                "input_tokens": 1_000_000,
                "output_tokens": 200,
                "actual_model": "actual-generation-model",
            }

    monkeypatch.setattr(
        router, "_adapter_for", lambda _provider: MalformedGenerationAdapter()
    )

    with pytest.raises(router.AIProviderUnavailable, match="provider_response_invalid"):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest(
                "Return JSON.",
                "content",
                "v1",
                response_schema={
                    "type": "object",
                    "properties": {"ok": {"type": "boolean"}},
                    "required": ["ok"],
                    "additionalProperties": False,
                },
            ),
        )

    run = AIAnalysisRun.objects.get()
    assert run.status == "failed"
    assert run.error_code == "provider_response_invalid"
    assert run.input_tokens == 1_000_000
    assert run.output_tokens == 200
    assert run.model_name == "actual-generation-model"
    assert str(run.reserved_cost) == "0.10010000"
    assert run.estimated_cost == run.reserved_cost


@pytest.mark.django_db
def test_daily_cost_guard_rejects_before_provider_execution(monkeypatch, project):
    _profile(parameters=_cost_parameters(daily_budget_usd="0.00001"))
    fake = _FakeAdapter()
    monkeypatch.setattr(router, "_adapter_for", lambda provider: fake)

    with pytest.raises(router.AICostLimitExceeded, match="daily_task_budget_exceeded"):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    assert fake.calls == 0
    assert not AIAnalysisRun.objects.exists()


@pytest.mark.django_db
def test_fallback_cost_guard_rejects_before_fallback_adapter_call(monkeypatch, project):
    primary = _profile(
        parameters=_cost_parameters(
            max_output_tokens=100, max_request_cost_usd="0.00015"
        )
    )
    fallback = _profile(
        profile_key="message-analysis-expensive-fallback",
        model_name="gpt-6.1-sol",
        is_default=False,
        parameters=_cost_parameters(
            input_usd_per_million_tokens="2.00",
            output_usd_per_million_tokens="10.00",
            max_request_cost_usd="10.00",
        ),
    )
    primary.fallback_profile = fallback
    primary.save()

    class PrimaryFailsAdapter:
        capabilities = _FakeAdapter.capabilities

        def __init__(self):
            self.calls = {}

        def generate(self, *, profile, request):
            self.calls[profile.profile_key] = self.calls.get(profile.profile_key, 0) + 1
            if profile.pk == primary.pk:
                raise ProviderCallError("provider_rate_limited", retryable=True)
            raise AssertionError("The over-budget fallback must not be called.")

    adapter = PrimaryFailsAdapter()
    monkeypatch.setattr(router, "_adapter_for", lambda provider: adapter)

    with pytest.raises(router.AICostLimitExceeded, match="fallback_cost_limit"):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    assert adapter.calls == {primary.profile_key: 2}
    run = AIAnalysisRun.objects.get()
    assert run.status == "failed"
    assert run.error_code == "fallback_cost_limit_exceeded"
    assert run.profile_id == primary.pk
    assert str(run.reserved_cost) == "0.00010260"


@pytest.mark.django_db
def test_fallback_cannot_raise_primary_task_daily_budget(monkeypatch, project):
    primary = _profile(
        parameters=_cost_parameters(max_output_tokens=100, daily_budget_usd="0.00012")
    )
    fallback = _profile(
        profile_key="message-analysis-high-budget-fallback",
        model_name="gpt-6.1-sol",
        is_default=False,
        parameters=_cost_parameters(
            input_usd_per_million_tokens="2.00",
            output_usd_per_million_tokens="10.00",
            max_request_cost_usd="10.00",
            daily_budget_usd="10.00",
        ),
    )
    primary.fallback_profile = fallback
    primary.save()

    class PrimaryFailsAdapter:
        capabilities = _FakeAdapter.capabilities

        def __init__(self):
            self.calls = {}

        def generate(self, *, profile, request):
            self.calls[profile.profile_key] = self.calls.get(profile.profile_key, 0) + 1
            if profile.pk == primary.pk:
                raise ProviderCallError("provider_rate_limited", retryable=True)
            raise AssertionError("The over-budget fallback must not be called.")

    adapter = PrimaryFailsAdapter()
    monkeypatch.setattr(router, "_adapter_for", lambda provider: adapter)
    with pytest.raises(router.AICostLimitExceeded, match="fallback_cost_limit"):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    run = AIAnalysisRun.objects.get()
    assert adapter.calls == {primary.profile_key: 2}
    assert run.error_code == "fallback_cost_limit_exceeded"
    assert run.profile_id == primary.pk
    assert str(run.reserved_cost) == "0.00010260"


@pytest.mark.django_db(transaction=True)
def test_concurrent_profile_reservations_share_a_task_budget_lock(project):
    assert connection.vendor == "postgresql"
    primary = _profile(
        parameters=_cost_parameters(max_output_tokens=100, daily_budget_usd="0.00006")
    )
    secondary = _profile(
        profile_key="message-analysis-secondary",
        is_default=False,
        parameters=_cost_parameters(max_output_tokens=100, daily_budget_usd="0.00006"),
    )
    attempt_started = Event()
    reservation_finished = Event()

    def reserve_secondary_profile():
        close_old_connections()
        try:
            attempt_started.set()
            return router._reserve_run(
                profile=secondary,
                task_key=AITask.MESSAGE_ANALYSIS,
                project_id=project.pk,
                prompt_version="v1",
                input_hash=f"{secondary.pk}",
                input_bytes=10,
            )
        finally:
            reservation_finished.set()
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        with transaction.atomic():
            router._lock_task_budget(AITask.MESSAGE_ANALYSIS)
            future = executor.submit(reserve_secondary_profile)
            assert attempt_started.wait(timeout=3)
            assert not reservation_finished.wait(timeout=0.2)
        future.result(timeout=5)

    with pytest.raises(router.AICostLimitExceeded, match="daily_task_budget"):
        router._reserve_run(
            profile=primary,
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            prompt_version="v1",
            input_hash=f"{primary.pk}",
            input_bytes=10,
        )
    assert AIAnalysisRun.objects.filter(task_key=AITask.MESSAGE_ANALYSIS).count() == 1


@pytest.mark.django_db
def test_missing_credentials_fails_explicitly_without_provider_call(
    monkeypatch, project
):
    _profile()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(
        router.AIProviderUnavailable, match="provider_credentials_missing"
    ):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    run = AIAnalysisRun.objects.get()
    assert run.status == "failed"
    assert run.error_code == "provider_credentials_missing"


@pytest.mark.django_db
def test_embedding_router_returns_versioned_batch_and_records_project(
    monkeypatch, project
):
    profile = _profile(
        task=AITask.DOCUMENT_EMBEDDING,
        profile_key="document-embedding-test",
        model_name="text-embedding-3-small",
        capabilities=[AICapability.EMBEDDINGS],
        parameters=_cost_parameters(
            dimensions=1536,
            input_usd_per_million_tokens="0.02",
            output_usd_per_million_tokens="0",
            max_output_tokens=0,
        ),
    )
    monkeypatch.setattr(router, "_ADAPTERS", {"openai": _FakeAdapter})

    batch = router.embed_texts(["one chunk"], project_id=project.pk)

    run = AIAnalysisRun.objects.get()
    assert batch.profile_key == profile.embedding_space_key
    assert batch.profile_version == profile.embedding_space_version
    assert len(batch.vectors[0]) == 1536
    assert run.project_id == project.pk
    assert run.status == "succeeded"


@pytest.mark.django_db
def test_embedding_space_identity_ignores_runtime_config_and_separates_models():
    profile = _profile(
        task=AITask.DOCUMENT_EMBEDDING,
        profile_key="embedding-small-space",
        model_name="text-embedding-3-small",
        capabilities=[AICapability.EMBEDDINGS],
        parameters=_cost_parameters(dimensions=1536, timeout_seconds=30),
    )
    stable_key = profile.embedding_space_key
    profile.parameters = _cost_parameters(dimensions=1536, timeout_seconds=60)
    profile.save()
    assert profile.config_version == 2
    assert profile.embedding_space_key == stable_key
    assert profile.embedding_space_version == 1

    profile.embedding_space_version = 2
    profile.save(update_fields=("embedding_space_version",))
    assert profile.config_version == 2
    assert profile.embedding_space_key == stable_key
    assert profile.embedding_space_version == 2

    next_model = _profile(
        task=AITask.DOCUMENT_EMBEDDING,
        profile_key="embedding-large-space",
        model_name="text-embedding-3-large",
        capabilities=[AICapability.EMBEDDINGS],
        parameters=_cost_parameters(dimensions=1536),
        is_default=False,
    )
    assert next_model.embedding_space_key != stable_key


@pytest.mark.django_db
def test_same_model_embedding_fallback_keeps_vector_space_identity(
    monkeypatch, project
):
    primary = _profile(
        task=AITask.DOCUMENT_EMBEDDING,
        profile_key="embedding-primary",
        model_name="text-embedding-3-small",
        capabilities=[AICapability.EMBEDDINGS],
        parameters=_cost_parameters(dimensions=1536),
    )
    fallback = _profile(
        task=AITask.DOCUMENT_EMBEDDING,
        profile_key="embedding-fallback-alias",
        model_name="text-embedding-3-small",
        capabilities=[AICapability.EMBEDDINGS],
        parameters=_cost_parameters(dimensions=1536),
        is_default=False,
    )
    primary.fallback_profile = fallback
    primary.save()

    class FlakyEmbeddingAdapter:
        capabilities = _FakeAdapter.capabilities

        def __init__(self):
            self.calls = {}

        def embed(self, *, profile, texts):
            self.calls[profile.profile_key] = self.calls.get(profile.profile_key, 0) + 1
            if profile.pk == primary.pk:
                raise ProviderCallError("provider_timeout", retryable=True)
            return {
                "vectors": [[1.0, *([0.0] * 1535)] for _ in texts],
                "input_tokens": 4,
                "actual_model": profile.model_name,
            }

    adapter = FlakyEmbeddingAdapter()
    monkeypatch.setattr(router, "_adapter_for", lambda provider: adapter)
    batch = router.embed_texts(["chunk"], project_id=project.pk)

    run = AIAnalysisRun.objects.get()
    assert adapter.calls == {primary.profile_key: 2, fallback.profile_key: 1}
    assert batch.profile_key == primary.embedding_space_key
    assert batch.profile_key == fallback.embedding_space_key
    assert batch.profile_version == primary.embedding_space_version
    assert run.profile_id == fallback.pk


@pytest.mark.django_db
def test_structured_reranker_scores_candidates_and_records_usage(monkeypatch, project):
    profile = _profile(
        task=AITask.RAG_RERANKING,
        profile_key="rag-reranking-test",
        model_name="gpt-6.1-sol",
        capabilities=[AICapability.RERANKING],
    )
    monkeypatch.setattr(router, "_ADAPTERS", {"openai": _FakeAdapter})

    ranked = router.rerank_candidates(
        task_key=AITask.RAG_RERANKING,
        project_id=project.pk,
        query="Which option supports exports?",
        candidates=["No exports", "CSV and JSON exports", "Email support"],
    )

    run = AIAnalysisRun.objects.get()
    assert [candidate.index for candidate in ranked] == [2, 1, 0]
    assert [candidate.score for candidate in ranked] == [2 / 3, 1 / 3, 0.0]
    assert run.profile_id == profile.pk
    assert run.task_key == AITask.RAG_RERANKING
    assert run.prompt_version == "rag-reranking-v1"
    assert run.status == "succeeded"
    assert run.input_tokens == 18
    assert run.output_tokens == 7


def test_openai_reranker_maps_structured_response_without_network(monkeypatch):
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                output_text='{"ranked_candidates":[{"index":1,"score":0.9},'
                '{"index":0,"score":0.2}]}',
                usage=SimpleNamespace(input_tokens=16, output_tokens=8),
                model="gpt-6.1-sol",
            )

    profile = SimpleNamespace(
        model_name="gpt-6.1-sol",
        parameters={
            "max_candidates": 10,
            "max_output_tokens": 512,
            "timeout_seconds": 45,
        },
    )
    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(openai_adapter, "OpenAI", lambda **kwargs: fake_client)

    result = OpenAIAdapter().rerank(
        profile=profile,
        query="export support",
        candidates=["no export", "CSV export"],
    )

    assert result["ranked_candidates"] == [
        {"index": 1, "score": 0.9},
        {"index": 0, "score": 0.2},
    ]
    assert result["input_tokens"] == 16
    assert result["output_tokens"] == 8
    assert result["actual_model"] == "gpt-6.1-sol"
    assert calls[0]["text"]["format"]["strict"] is True
    assert calls[0]["text"]["format"]["schema"] == OpenAIAdapter._RERANK_SCHEMA


@pytest.mark.django_db
def test_reranker_rejects_invalid_candidate_indexes(monkeypatch, project):
    _profile(
        task=AITask.RAG_RERANKING,
        profile_key="rag-reranking-invalid-output",
        model_name="gpt-6.1-sol",
        capabilities=[AICapability.RERANKING],
    )

    class InvalidReranker:
        capabilities = _FakeAdapter.capabilities

        def rerank(self, *, profile, query, candidates):
            return {
                "ranked_candidates": [
                    {"index": 0, "score": 0.9},
                    {"index": 0, "score": 0.5},
                ],
                "input_tokens": 10,
                "output_tokens": 5,
                "actual_model": profile.model_name,
            }

    monkeypatch.setattr(router, "_adapter_for", lambda provider: InvalidReranker())
    with pytest.raises(router.AIProviderUnavailable, match="provider_response_invalid"):
        router.rerank_candidates(
            task_key=AITask.RAG_RERANKING,
            project_id=project.pk,
            query="query",
            candidates=["first", "second"],
        )

    run = AIAnalysisRun.objects.get()
    assert run.status == "failed"
    assert run.error_code == "provider_response_invalid"


@pytest.mark.django_db
def test_invalid_rerank_result_retains_billable_usage_and_cost(monkeypatch, project):
    _profile(
        task=AITask.RAG_RERANKING,
        profile_key="rag-reranking-billable-invalid",
        capabilities=[AICapability.RERANKING],
        parameters=_cost_parameters(),
    )

    class BillableInvalidReranker:
        capabilities = _FakeAdapter.capabilities

        def rerank(self, *, profile, query, candidates):
            return {
                "ranked_candidates": [
                    {"index": 0, "score": 0.9},
                    {"index": 0, "score": 0.1},
                ],
                "input_tokens": 1_000_000,
                "output_tokens": 200,
                "actual_model": "actual-rerank-model",
            }

    monkeypatch.setattr(
        router,
        "_adapter_for",
        lambda _provider: BillableInvalidReranker(),
    )

    with pytest.raises(router.AIProviderUnavailable, match="provider_response_invalid"):
        router.rerank_candidates(
            task_key=AITask.RAG_RERANKING,
            project_id=project.pk,
            query="query",
            candidates=["first", "second"],
        )

    run = AIAnalysisRun.objects.get()
    assert run.status == "failed"
    assert run.error_code == "provider_response_invalid"
    assert run.input_tokens == 1_000_000
    assert run.output_tokens == 200
    assert run.model_name == "actual-rerank-model"
    assert str(run.reserved_cost) == "0.10010000"
    assert run.estimated_cost == run.reserved_cost


@pytest.mark.django_db
def test_openai_408_retries_once_and_maps_success_usage(monkeypatch, project):
    from openai import APIStatusError

    profile = _profile()
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise APIStatusError(
                    "request timed out",
                    response=SimpleNamespace(
                        status_code=408,
                        request=SimpleNamespace(),
                        headers={},
                    ),
                    body=None,
                )
            return SimpleNamespace(
                output_text="The answer",
                usage=SimpleNamespace(input_tokens=20, output_tokens=4),
                model="gpt-6-luna",
            )

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(openai_adapter, "OpenAI", lambda **kwargs: fake_client)

    response = router.generate_text(
        task_key=AITask.MESSAGE_ANALYSIS,
        project_id=project.pk,
        request=TextGenerationRequest("system", "content", "v1"),
    )

    run = AIAnalysisRun.objects.get()
    assert response.text == "The answer"
    assert response.provider_key == "openai"
    assert response.model_name == "gpt-6-luna"
    assert run.status == "succeeded"
    assert run.attempt_count == 2
    assert run.input_tokens == 20
    assert run.output_tokens == 4
    assert len(calls) == 2
    assert calls[0]["model"] == profile.model_name


@pytest.mark.django_db
def test_openai_malformed_generation_retains_usage_and_overrun(monkeypatch, project):
    _profile()

    class IncompleteResponse:
        usage = SimpleNamespace(input_tokens=1_000_000, output_tokens=200)
        model = "actual-generation-model"

        @property
        def output_text(self):
            raise AttributeError("response has no complete output text")

    fake_client = SimpleNamespace(
        responses=SimpleNamespace(create=lambda **_kwargs: IncompleteResponse())
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(openai_adapter, "OpenAI", lambda **_kwargs: fake_client)

    with pytest.raises(router.AIProviderUnavailable, match="provider_response_invalid"):
        router.generate_text(
            task_key=AITask.MESSAGE_ANALYSIS,
            project_id=project.pk,
            request=TextGenerationRequest("system", "content", "v1"),
        )

    run = AIAnalysisRun.objects.get()
    assert run.status == "failed"
    assert run.input_tokens == 1_000_000
    assert run.output_tokens == 200
    assert run.model_name == "actual-generation-model"
    assert str(run.reserved_cost) == "0.10010000"


@pytest.mark.django_db
def test_openai_malformed_rerank_retains_usage_and_overrun(monkeypatch, project):
    _profile(
        task=AITask.RAG_RERANKING,
        profile_key="rag-reranking-openai-malformed",
        model_name="gpt-6.1-sol",
        capabilities=[AICapability.RERANKING],
    )
    fake_client = SimpleNamespace(
        responses=SimpleNamespace(
            create=lambda **_kwargs: SimpleNamespace(
                output_text="not-json",
                usage=SimpleNamespace(input_tokens=1_000_000, output_tokens=200),
                model="actual-reranker-model",
            )
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(openai_adapter, "OpenAI", lambda **_kwargs: fake_client)

    with pytest.raises(router.AIProviderUnavailable, match="provider_response_invalid"):
        router.rerank_candidates(
            task_key=AITask.RAG_RERANKING,
            project_id=project.pk,
            query="query",
            candidates=["first", "second"],
        )

    run = AIAnalysisRun.objects.get()
    assert run.status == "failed"
    assert run.input_tokens == 1_000_000
    assert run.output_tokens == 200
    assert run.model_name == "actual-reranker-model"
    assert str(run.reserved_cost) == "0.10010000"


@pytest.mark.django_db
def test_openai_invalid_embedding_batch_retains_usage_and_overrun(monkeypatch, project):
    _profile(
        task=AITask.DOCUMENT_EMBEDDING,
        profile_key="embedding-openai-malformed",
        model_name="text-embedding-3-small",
        capabilities=[AICapability.EMBEDDINGS],
        parameters=_cost_parameters(dimensions=1536, max_output_tokens=0),
    )
    fake_client = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=lambda **_kwargs: SimpleNamespace(
                data=[],
                usage=SimpleNamespace(prompt_tokens=1_000_000),
                model="actual-embedding-model",
            )
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(openai_adapter, "OpenAI", lambda **_kwargs: fake_client)

    with pytest.raises(router.AIProviderUnavailable, match="provider_response_invalid"):
        router.embed_texts(["chunk"], project_id=project.pk)

    run = AIAnalysisRun.objects.get()
    assert run.status == "failed"
    assert run.input_tokens == 1_000_000
    assert run.output_tokens is None
    assert run.model_name == "actual-embedding-model"
    assert str(run.reserved_cost) == "0.10000000"


def test_openai_adapter_normalizes_missing_credentials_without_network(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ProviderCallError) as error:
        OpenAIAdapter().generate(
            profile=SimpleNamespace(
                parameters={"timeout_seconds": 1}, model_name="gpt-6-luna"
            ),
            request=TextGenerationRequest("system", "content", "v1"),
        )

    assert error.value.code == "provider_credentials_missing"


@pytest.mark.django_db
def test_admin_profile_configuration_is_staff_only(client, project):
    profile = _profile()
    anonymous = client.get(f"/admin/ai_assistant/aimodelprofile/{profile.pk}/change/")
    assert anonymous.status_code == 302

    regular = User.objects.create_user(email="regular-ai@example.com")
    client.force_login(regular)
    response = client.get(f"/admin/ai_assistant/aimodelprofile/{profile.pk}/change/")
    assert response.status_code == 302

    staff = User.objects.create_user(email="staff-ai@example.com", is_staff=True)
    staff.user_permissions.add(
        Permission.objects.get(
            codename="change_aimodelprofile",
            content_type__app_label="ai_assistant",
        )
    )
    client.force_login(staff)
    response = client.get(f"/admin/ai_assistant/aimodelprofile/{profile.pk}/change/")
    assert response.status_code == 200
