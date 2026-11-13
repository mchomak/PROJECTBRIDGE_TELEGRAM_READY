from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Lock
from types import SimpleNamespace
from uuid import uuid4

import pytest
from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.db import OperationalError, close_old_connections
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ai_assistant.models import (
    AIAnalysisRequest,
    AIAnalysisRun,
    AIProposal,
    AIProposalType,
)
from apps.project_state.models import (
    OpenQuestion,
    ProjectConflict,
    ProjectStage,
    Requirement,
    Task,
)
from apps.projects.models import ProjectMember
from apps.projects.services import create_project
from apps.specifications.models import (
    Specification,
    SpecificationGenerationRequest,
    SpecificationGenerationStatus,
)
from apps.specifications.services import (
    complete_generation_request,
    queue_specification_generation,
    update_specification,
)


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def project_context():
    user_model = get_user_model()
    executor = user_model.objects.create_user(email="spec-executor@example.com")
    customer = user_model.objects.create_user(email="spec-customer@example.com")
    outsider = user_model.objects.create_user(email="spec-outsider@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Specification project", "project_type": "website"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )
    other_project = create_project(
        actor=outsider,
        data={"name": "Other specification project", "project_type": "other"},
    )
    return project, executor, customer, outsider, other_project


@pytest.mark.django_db
def test_both_members_read_but_only_executor_can_edit_or_generate(project_context):
    project, executor, customer, outsider, _ = project_context
    executor_client = _client(executor)
    customer_client = _client(customer)
    outsider_client = _client(outsider)
    url = f"/api/v1/projects/{project.pk}/specification/"

    executor_read = executor_client.get(url)
    customer_read = customer_client.get(url)
    assert executor_read.status_code == 200
    assert customer_read.status_code == 200
    assert executor_read.data["content"] == ""
    assert executor_read.data["version"] == 1
    assert customer_read.data["generation"] is None

    customer_edit = customer_client.patch(
        url,
        {"content": "Customer edit", "version": 1},
        format="json",
    )
    customer_generate = customer_client.post(
        f"{url}generate/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    outsider_read = outsider_client.get(url)

    assert customer_edit.status_code == 403
    assert customer_generate.status_code == 403
    assert outsider_read.status_code == 404


@pytest.mark.django_db
def test_patch_uses_optimistic_version_and_rejects_unknown_fields(project_context):
    project, executor, *_ = project_context
    client = _client(executor)
    url = f"/api/v1/projects/{project.pk}/specification/"

    saved = client.patch(
        url,
        {"content": "# Current draft\n", "version": 1},
        format="json",
    )
    stale = client.patch(
        url,
        {"content": "Stale overwrite", "version": 1},
        format="json",
    )
    unknown = client.patch(
        url,
        {"content": "Extra field", "version": 2, "approved": True},
        format="json",
    )
    missing_version = client.patch(
        url,
        {"content": "No version"},
        format="json",
    )
    missing_content = client.patch(
        url,
        {"version": 2},
        format="json",
    )

    assert saved.status_code == 200
    assert saved.data["version"] == 2
    assert saved.data["content"] == "# Current draft\n"
    assert stale.status_code == 409
    assert stale.data["code"] == "conflict"
    assert unknown.status_code == 400
    assert missing_version.status_code == 400
    assert missing_content.status_code == 400
    assert Specification.objects.get(project=project).content == "# Current draft\n"


@pytest.mark.django_db(transaction=True)
def test_concurrent_patch_same_version_has_one_winner(project_context, monkeypatch):
    project, executor, *_ = project_context
    from apps.specifications.services import get_specification

    assert get_specification(project_id=project.pk, actor=executor).version == 1
    url = f"/api/v1/projects/{project.pk}/specification/"
    update_barrier = Barrier(2)

    from apps.specifications.api import views

    real_update = views.update_specification

    def synchronized_update(**kwargs):
        update_barrier.wait(timeout=10)
        return real_update(**kwargs)

    monkeypatch.setattr(views, "update_specification", synchronized_update)

    def patch(content):
        close_old_connections()
        try:
            response = _client(executor).patch(
                url,
                {"content": content, "version": 1},
                format="json",
            )
            return response.status_code, response.data
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(patch, "# Parallel draft A"),
            pool.submit(patch, "# Parallel draft B"),
        ]
        responses = [future.result(timeout=20) for future in futures]

    winners = [(code, data) for code, data in responses if code == 200]
    conflicts = [(code, data) for code, data in responses if code == 409]
    assert len(winners) == 1
    assert len(conflicts) == 1
    winning_content = winners[0][1]["content"]
    assert winners[0][1]["version"] == 2
    assert conflicts[0][1]["code"] == "conflict"

    specification = Specification.objects.get(project=project)
    assert specification.version == 2
    assert specification.content == winning_content
    assert winning_content in {"# Parallel draft A", "# Parallel draft B"}


@pytest.mark.django_db
def test_openapi_requires_content_and_version_for_specification_patch():
    from drf_spectacular.generators import SchemaGenerator

    schema = SchemaGenerator().get_schema(request=None, public=True)
    request_schema = schema["paths"]["/api/v1/projects/{project_id}/specification/"][
        "patch"
    ]["requestBody"]["content"]["application/json"]["schema"]
    request_component = schema["components"]["schemas"][
        request_schema["$ref"].split("/")[-1]
    ]

    assert {"content", "version"} <= set(request_component["required"])


@pytest.mark.django_db
def test_generation_enqueue_is_idempotent_and_returns_request_status(project_context):
    project, executor, *_ = project_context
    client = _client(executor)
    url = f"/api/v1/projects/{project.pk}/specification/generate/"
    key = str(uuid4())

    first = client.post(url, {}, format="json", HTTP_IDEMPOTENCY_KEY=key)
    retry = client.post(url, {}, format="json", HTTP_IDEMPOTENCY_KEY=key)

    assert first.status_code == 202
    assert retry.status_code == 202
    assert first.data["id"] == retry.data["id"]
    assert first.data["status"] == "queued"
    assert "source_context_hash" not in first.data
    assert SpecificationGenerationRequest.objects.filter(project=project).count() == 1
    assert (
        client.get(f"/api/v1/projects/{project.pk}/specification/").data["generation"][
            "id"
        ]
        == first.data["id"]
    )


@pytest.mark.django_db(transaction=True)
def test_beat_recovers_dispatch_lost_after_database_commit(
    monkeypatch, project_context
):
    from django.conf import settings

    from apps.specifications import services, tasks

    project, executor, *_ = project_context
    real_enqueue = services._enqueue_generation
    monkeypatch.setattr(services, "_enqueue_generation", lambda **kwargs: None)
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    monkeypatch.setattr(services, "_enqueue_generation", real_enqueue)
    request.refresh_from_db()
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert request.dispatch_attempts == 0
    assert request.dispatch_lease_expires_at is None

    SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now()
        - services.GENERATION_DISPATCH_STALE_AFTER
        - timedelta(seconds=1)
    )
    dispatched = []
    monkeypatch.setattr(
        tasks.generate_specification,
        "apply_async",
        lambda *, args, task_id: dispatched.append((args, task_id)),
    )

    recovered = tasks.recover_stale_specification_generations.run()

    request.refresh_from_db()
    assert recovered == 1
    assert dispatched == [((str(request.pk),), str(request.celery_task_id))]
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert request.dispatch_attempts == 1
    assert request.dispatch_lease_expires_at > timezone.now()
    assert (
        settings.CELERY_BEAT_SCHEDULE["specification-generation-dispatch-recovery"][
            "task"
        ]
        == "apps.specifications.tasks.recover_stale_specification_generations"
    )


@pytest.mark.django_db(transaction=True)
def test_successful_specification_publishes_keep_the_original_fifo_message_valid(
    monkeypatch, project_context
):
    from apps.specifications import services, tasks

    project, executor, *_ = project_context
    real_enqueue = services._enqueue_generation
    monkeypatch.setattr(services, "_enqueue_generation", lambda **_kwargs: None)
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    monkeypatch.setattr(services, "_enqueue_generation", real_enqueue)
    SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    publications = []
    monkeypatch.setattr(
        tasks.generate_specification,
        "apply_async",
        lambda *, args, task_id: publications.append((args, task_id)),
    )
    for _ in range(7):
        SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
            dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert tasks.recover_stale_specification_generations.run() == 1

    request.refresh_from_db()
    original_publication = ((str(request.pk),), str(request.celery_task_id))
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert request.dispatch_attempts == 7
    assert request.error_code == "worker_backlog"
    assert publications == [original_publication] * 7

    def broker_unavailable(*, args, task_id):
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(tasks.generate_specification, "apply_async", broker_unavailable)
    for _ in range(5):
        SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
            dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert tasks.recover_stale_specification_generations.run() == 0

    request.refresh_from_db()
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert request.execution_generation == 0
    assert request.dispatch_failures == 5

    state, generation, *_ = services.claim_generation_request(
        request_id=publications[0][0][0]
    )
    assert state == "claimed"
    assert generation == 1
    request.refresh_from_db()
    assert request.error_code == ""
    assert request.dispatch_attempts == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_beat_recovery_dispatches_a_queued_request_once(
    monkeypatch, project_context
):
    from apps.specifications import services, tasks

    project, executor, *_ = project_context
    real_enqueue = services._enqueue_generation
    monkeypatch.setattr(services, "_enqueue_generation", lambda **kwargs: None)
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    monkeypatch.setattr(services, "_enqueue_generation", real_enqueue)
    SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now()
        - services.GENERATION_DISPATCH_STALE_AFTER
        - timedelta(seconds=1)
    )

    candidate_barrier = Barrier(2)
    dispatched = []
    dispatch_lock = Lock()
    real_candidates = services._stale_generation_dispatch_candidates

    def synchronized_candidates():
        candidates = real_candidates()
        candidate_barrier.wait(timeout=10)
        return candidates

    def fake_apply_async(*, args, task_id):
        with dispatch_lock:
            dispatched.append((args, task_id))

    monkeypatch.setattr(
        services,
        "_stale_generation_dispatch_candidates",
        synchronized_candidates,
    )
    monkeypatch.setattr(
        tasks.generate_specification,
        "apply_async",
        fake_apply_async,
    )

    def run_recovery():
        close_old_connections()
        try:
            return tasks.recover_stale_specification_generations.run()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(run_recovery)
        second = pool.submit(run_recovery)
        results = [first.result(timeout=10), second.result(timeout=10)]

    request.refresh_from_db()
    assert sorted(results) == [0, 1]
    assert dispatched == [((str(request.pk),), str(request.celery_task_id))]
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert request.dispatch_attempts == 1


@pytest.mark.django_db
def test_ambiguous_generation_publishes_keep_the_first_fifo_message(
    monkeypatch, project_context
):
    from apps.specifications import services, tasks

    project, executor, *_ = project_context
    monkeypatch.setattr(services.transaction, "on_commit", lambda callback: callback())
    publish_calls = []

    def accepted_then_raised(*, args, task_id):
        publish_calls.append((args, task_id))
        raise ConnectionError("publish acknowledgment was lost")

    monkeypatch.setattr(
        tasks.generate_specification, "apply_async", accepted_then_raised
    )
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    for _ in range(4):
        SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
            dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert tasks.recover_stale_specification_generations.run() == 0

    request.refresh_from_db()
    expected = ((str(request.pk),), str(request.celery_task_id))
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert request.execution_generation == 0
    assert request.dispatch_attempts == 5
    assert request.dispatch_failures == 5
    assert request.error_code == "queue_unavailable"
    assert publish_calls == [expected] * 5

    provider_calls = []

    def fake_generate_text(**kwargs):
        provider_calls.append(kwargs)
        return SimpleNamespace(text="# Processed from the FIFO head")

    monkeypatch.setattr(tasks, "generate_text", fake_generate_text)
    assert tasks.generate_specification.run(*publish_calls[0][0]) == "succeeded"
    assert tasks.generate_specification.run(*publish_calls[1][0]) == "succeeded"

    request.refresh_from_db()
    assert request.status == SpecificationGenerationStatus.SUCCEEDED
    assert request.execution_generation == 1
    assert request.error_code == ""
    assert len(provider_calls) == 1
    assert Specification.objects.get(project=project).content == (
        "# Processed from the FIFO head"
    )


@pytest.mark.django_db(transaction=True)
def test_dispatch_failures_surface_warning_and_automatic_recovery_keeps_generation(
    monkeypatch, project_context
):
    from apps.specifications import services, tasks

    project, executor, *_ = project_context
    real_enqueue = services._enqueue_generation
    monkeypatch.setattr(services, "_enqueue_generation", lambda **kwargs: None)
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    monkeypatch.setattr(services, "_enqueue_generation", real_enqueue)
    SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now()
        - services.GENERATION_DISPATCH_STALE_AFTER
        - timedelta(seconds=1)
    )
    failed_publications = []

    def broker_unavailable(*, args, task_id):
        failed_publications.append((args, task_id))
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(tasks.generate_specification, "apply_async", broker_unavailable)
    for _ in range(services.MAX_GENERATION_DISPATCH_FAILURES):
        SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
            dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert tasks.recover_stale_specification_generations.run() == 0

    request.refresh_from_db()
    assert request.dispatch_attempts == services.MAX_GENERATION_DISPATCH_FAILURES
    assert request.dispatch_failures == services.MAX_GENERATION_DISPATCH_FAILURES
    assert request.dispatch_successful_at is None
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert request.error_code == "queue_unavailable"
    assert request.execution_generation == 0

    dispatched = []
    monkeypatch.setattr(
        tasks.generate_specification,
        "apply_async",
        lambda **kwargs: dispatched.append(kwargs),
    )

    SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
        dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1)
    )
    recovered = tasks.recover_stale_specification_generations.run()

    request.refresh_from_db()
    assert recovered == 1
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert request.error_code == "worker_backlog"
    assert len(failed_publications) == services.MAX_GENERATION_DISPATCH_FAILURES
    assert dispatched == [
        {"args": (str(request.pk),), "task_id": str(request.celery_task_id)}
    ]
    assert request.execution_generation == 0
    state, generation, *_ = services.claim_generation_request(
        request_id=failed_publications[0][0][0]
    )
    assert state == "claimed"
    assert generation == 1
    request.refresh_from_db()
    assert request.error_code == ""


@pytest.mark.django_db(transaction=True)
def test_specification_success_marker_save_failure_preserves_accepted_fifo(
    monkeypatch, project_context
):
    from apps.specifications import services, tasks

    project, executor, *_ = project_context
    monkeypatch.setattr(services.transaction, "on_commit", lambda callback: callback())
    real_success_marker = services._record_generation_dispatch_success
    publications = []
    monkeypatch.setattr(
        tasks.generate_specification,
        "apply_async",
        lambda *, args, task_id: publications.append((args, task_id)),
    )

    def fail_success_marker(**_kwargs):
        raise OperationalError("temporary marker write failure")

    monkeypatch.setattr(
        services, "_record_generation_dispatch_success", fail_success_marker
    )
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    assert len(publications) == 1
    assert request.dispatch_successful_at is None
    SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
        created_at=timezone.now() - timedelta(days=1),
        dispatch_lease_expires_at=timezone.now() - timedelta(seconds=1),
    )
    monkeypatch.setattr(
        services, "_record_generation_dispatch_success", real_success_marker
    )
    assert tasks.recover_stale_specification_generations.run() == 1

    request.refresh_from_db()
    assert request.dispatch_successful_at is not None
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert request.execution_generation == 0
    expected = ((str(request.pk),), str(request.celery_task_id))
    assert publications == [expected, expected]
    state, generation, *_ = services.claim_generation_request(
        request_id=publications[0][0][0]
    )
    assert state == "claimed"
    assert generation == 1
    duplicate_state, duplicate_generation, *_ = services.claim_generation_request(
        request_id=publications[1][0][0]
    )
    assert duplicate_state == "busy"
    assert duplicate_generation == 1


@pytest.mark.django_db
def test_generation_uses_router_and_publishes_once(monkeypatch, project_context):
    project, executor, *_ = project_context
    OpenQuestion.objects.create(
        project=project,
        created_by=executor,
        question="Which option is not settled?",
    )
    ProjectConflict.objects.create(
        project=project,
        created_by=executor,
        title="Unresolved choice",
        description="Option A conflicts with option B.",
    )
    OpenQuestion.objects.create(
        project=project,
        created_by=executor,
        question="Dismissed product idea",
        status="dismissed",
    )
    ProjectConflict.objects.create(
        project=project,
        created_by=executor,
        title="Dismissed conflict",
        description="This claim was not adopted.",
        status="dismissed",
    )
    run = AIAnalysisRun.objects.create(
        project=project,
        task_key="contradiction_detection",
        provider_key="openai",
        model_name="test-model",
        profile_version=1,
        input_hash="a" * 64,
    )
    ai_request = AIAnalysisRequest.objects.create(
        project=project,
        requested_by=executor,
        run=run,
    )
    AIProposal.objects.create(
        project=project,
        analysis_run=run,
        analysis_request=ai_request,
        idempotency_key="private-pending-test",
        proposal_type=AIProposalType.REQUIREMENT_CREATE,
        title="PRIVATE_PENDING_PROPOSAL",
        description="This must not be used in the shared specification.",
        proposed_payload={"title": "PRIVATE_PENDING_REQUIREMENT"},
    )
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    calls = []

    def fake_generate_text(*, task_key, project_id, request):
        calls.append((task_key, project_id, request))
        return SimpleNamespace(text="# Generated\n\nFrom approved context.")

    monkeypatch.setattr("apps.specifications.tasks.generate_text", fake_generate_text)
    from apps.specifications.tasks import generate_specification

    result = generate_specification.run(str(request.pk))
    replay = generate_specification.run(str(request.pk))

    specification = Specification.objects.get(project=project)
    request.refresh_from_db()
    assert result == "succeeded"
    assert replay == "succeeded"
    assert len(calls) == 1
    assert calls[0][0] == "specification_generation"
    assert calls[0][1] == project.pk
    assert "project" in calls[0][2].user_input
    assert "UNRESOLVED" in calls[0][2].user_input
    assert "Unresolved choice" in calls[0][2].user_input
    assert (
        "DISMISSED: this question was not adopted as a decision or fact."
        in calls[0][2].user_input
    )
    assert (
        "DISMISSED: neither conflicting claim was adopted as fact."
        in calls[0][2].user_input
    )
    assert "PRIVATE_PENDING_PROPOSAL" not in calls[0][2].user_input
    assert "PRIVATE_PENDING_REQUIREMENT" not in calls[0][2].user_input
    assert specification.content == "# Generated\n\nFrom approved context."
    assert specification.version == 2
    assert request.status == SpecificationGenerationStatus.SUCCEEDED


@pytest.mark.django_db
def test_transient_claim_failure_retries_before_calling_router(
    monkeypatch, project_context
):
    project, executor, *_ = project_context
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    from apps.specifications import tasks

    real_claim = tasks.claim_generation_request
    claims = 0
    provider_calls = 0

    def transient_claim(*, request_id):
        nonlocal claims
        claims += 1
        if claims == 1:
            raise OperationalError("temporary database connection failure")
        return real_claim(request_id=request_id)

    def fake_generate_text(**kwargs):
        nonlocal provider_calls
        provider_calls += 1
        return SimpleNamespace(text="# Recovered generation")

    monkeypatch.setattr(tasks, "claim_generation_request", transient_claim)
    monkeypatch.setattr(tasks, "generate_text", fake_generate_text)
    tasks.generate_specification.push_request(called_directly=False, is_eager=True)
    try:
        with pytest.raises(Retry) as retry_info:
            tasks.generate_specification.run(str(request.pk))
    finally:
        tasks.generate_specification.pop_request()

    assert retry_info.value.when == tasks.CLAIM_RECOVERY_DELAY_SECONDS
    assert isinstance(retry_info.value.exc, OperationalError)
    request.refresh_from_db()
    assert request.status == SpecificationGenerationStatus.QUEUED
    assert provider_calls == 0

    result = tasks.generate_specification.run(str(request.pk))

    request.refresh_from_db()
    assert result == "succeeded"
    assert claims == 2
    assert provider_calls == 1
    assert request.status == SpecificationGenerationStatus.SUCCEEDED
    assert (
        Specification.objects.get(project=project).content == "# Recovered generation"
    )


@pytest.mark.django_db
def test_transient_publish_failure_retries_persistence_without_second_provider_call(
    monkeypatch, project_context
):
    project, executor, *_ = project_context
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    from apps.specifications import tasks

    real_complete = tasks.complete_generation_request
    publish_calls = 0
    provider_calls = 0

    def fail_first_publish(**kwargs):
        nonlocal publish_calls
        publish_calls += 1
        if publish_calls == 1:
            raise OperationalError("temporary database failure after generation")
        return real_complete(**kwargs)

    def fake_generate_text(**kwargs):
        nonlocal provider_calls
        provider_calls += 1
        return SimpleNamespace(text="# Persisted after retry")

    monkeypatch.setattr(tasks, "complete_generation_request", fail_first_publish)
    monkeypatch.setattr(tasks, "generate_text", fake_generate_text)

    result = tasks.generate_specification.run(str(request.pk))

    request.refresh_from_db()
    assert result == "succeeded"
    assert publish_calls == 2
    assert provider_calls == 1
    assert request.status == SpecificationGenerationStatus.SUCCEEDED
    assert (
        Specification.objects.get(project=project).content == "# Persisted after retry"
    )


@pytest.mark.django_db
def test_exhausted_publish_retry_is_recovered_after_lease_expiry(
    monkeypatch, project_context
):
    project, executor, *_ = project_context
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    from apps.specifications import tasks

    provider_calls = 0
    publish_calls = 0

    def fake_generate_text(**kwargs):
        nonlocal provider_calls
        provider_calls += 1
        return SimpleNamespace(text=f"# Recovered generation {provider_calls}")

    def fail_publish(**kwargs):
        nonlocal publish_calls
        publish_calls += 1
        raise OperationalError("database unavailable during publish")

    monkeypatch.setattr(tasks, "generate_text", fake_generate_text)
    monkeypatch.setattr(tasks, "complete_generation_request", fail_publish)

    tasks.generate_specification.push_request(called_directly=False, is_eager=True)
    try:
        with pytest.raises(Retry) as retry_info:
            tasks.generate_specification.run(str(request.pk))
    finally:
        tasks.generate_specification.pop_request()

    assert retry_info.value.when == tasks.CLAIM_RECOVERY_DELAY_SECONDS
    assert publish_calls == tasks.PUBLISH_ATTEMPTS
    assert provider_calls == 1
    request.refresh_from_db()
    assert request.status == SpecificationGenerationStatus.RUNNING
    assert request.lease_expires_at is not None

    SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
        lease_expires_at=timezone.now() - timedelta(seconds=1)
    )
    monkeypatch.setattr(
        tasks,
        "complete_generation_request",
        complete_generation_request,
    )
    result = tasks.generate_specification.run(str(request.pk))

    request.refresh_from_db()
    assert result == "succeeded"
    assert request.status == SpecificationGenerationStatus.SUCCEEDED
    assert request.execution_generation == 2
    assert provider_calls == 2
    assert (
        Specification.objects.get(project=project).content == "# Recovered generation 2"
    )


@pytest.mark.django_db
def test_duplicate_delivery_during_active_lease_retries_without_provider_call(
    monkeypatch, project_context
):
    project, executor, *_ = project_context
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    from apps.specifications import tasks
    from apps.specifications.services import claim_generation_request

    state, generation, *_ = claim_generation_request(request_id=str(request.pk))
    provider_calls = []
    monkeypatch.setattr(
        tasks,
        "generate_text",
        lambda **kwargs: provider_calls.append(kwargs),
    )

    tasks.generate_specification.push_request(called_directly=False, is_eager=True)
    try:
        with pytest.raises(Retry) as retry_info:
            tasks.generate_specification.run(str(request.pk))
    finally:
        tasks.generate_specification.pop_request()

    request.refresh_from_db()
    assert state == "claimed"
    assert generation == 1
    assert 1 <= retry_info.value.when <= 60
    assert provider_calls == []
    assert request.status == SpecificationGenerationStatus.RUNNING
    assert request.execution_generation == generation


@pytest.mark.django_db
def test_expired_lease_reclaims_with_fencing_against_old_worker(project_context):
    project, executor, *_ = project_context
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    from apps.specifications.services import (
        claim_generation_request,
        fail_generation_request,
    )

    state, old_generation, *_ = claim_generation_request(request_id=str(request.pk))
    SpecificationGenerationRequest.objects.filter(pk=request.pk).update(
        lease_expires_at=timezone.now() - timedelta(seconds=1)
    )
    reclaimed, new_generation, *_ = claim_generation_request(request_id=str(request.pk))

    assert state == "claimed"
    assert reclaimed == "claimed"
    assert new_generation == old_generation + 1
    assert (
        complete_generation_request(
            request_id=request.pk,
            generation=old_generation,
            content="# Stale worker publish",
        )
        is False
    )
    assert (
        fail_generation_request(
            request_id=request.pk,
            generation=old_generation,
            error=RuntimeError("stale worker failure"),
        )
        is False
    )

    request.refresh_from_db()
    assert request.status == SpecificationGenerationStatus.RUNNING
    assert request.execution_generation == new_generation
    assert (
        complete_generation_request(
            request_id=request.pk,
            generation=new_generation,
            content="# Current worker publish",
        )
        is True
    )
    assert (
        complete_generation_request(
            request_id=request.pk,
            generation=old_generation,
            content="# Late stale worker publish",
        )
        is False
    )
    assert (
        fail_generation_request(
            request_id=request.pk,
            generation=old_generation,
            error=RuntimeError("late stale worker failure"),
        )
        is False
    )
    request.refresh_from_db()
    assert request.status == SpecificationGenerationStatus.SUCCEEDED
    assert (
        Specification.objects.get(project=project).content == "# Current worker publish"
    )


@pytest.mark.django_db
def test_generation_context_excludes_chat_and_document_content(
    monkeypatch, settings, tmp_path, project_context
):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.chat.services import send_message
    from apps.documents.services import upload_document
    from apps.specifications.prompts import build_specification_request
    from apps.specifications.selectors import get_specification_generation_context

    project, executor, *_ = project_context
    project.status = "active"
    project.save(update_fields=("status",))
    settings.MEDIA_ROOT = tmp_path
    send_message(
        project_id=project.pk,
        actor=executor,
        client_message_id=uuid4(),
        content="CHAT_PRIVATE_SENTINEL: customer message body",
    )
    upload_document(
        project_id=project.pk,
        actor=executor,
        file=SimpleUploadedFile(
            "project-notes.txt",
            b"DOCUMENT_PRIVATE_SENTINEL: uploaded source text",
        ),
    )

    context = get_specification_generation_context(project=project, actor=executor)
    prompt = build_specification_request(context)

    assert "CHAT_PRIVATE_SENTINEL" not in repr(context)
    assert "CHAT_PRIVATE_SENTINEL" not in prompt.user_input
    assert "DOCUMENT_PRIVATE_SENTINEL" not in repr(context)
    assert "DOCUMENT_PRIVATE_SENTINEL" not in prompt.user_input
    assert "documents, chat, and RAG are excluded" in prompt.user_input


@pytest.mark.django_db
def test_context_labels_all_shared_state_statuses_and_excludes_project_metadata(
    project_context,
):
    from apps.specifications.prompts import build_specification_request
    from apps.specifications.selectors import get_specification_generation_context

    project, executor, *_ = project_context
    stage_statuses = ("planned", "active", "blocked", "completed", "cancelled")
    requirement_statuses = (
        "draft",
        "confirmed",
        "in_progress",
        "blocked",
        "completed",
        "rejected",
    )
    task_statuses = ("todo", "in_progress", "blocked", "done", "cancelled")
    question_statuses = ("open", "resolved", "dismissed")
    conflict_statuses = ("unresolved", "resolved", "dismissed")

    for position, state in enumerate(stage_statuses):
        ProjectStage.objects.create(
            project=project,
            created_by=executor,
            name=f"Stage {state}",
            position=position,
            status=state,
        )
    for state in requirement_statuses:
        Requirement.objects.create(
            project=project,
            created_by=executor,
            title=f"Requirement {state}",
            status=state,
        )
    for state in task_statuses:
        Task.objects.create(
            project=project,
            created_by=executor,
            title=f"Task {state}",
            status=state,
        )
    for state in question_statuses:
        OpenQuestion.objects.create(
            project=project,
            created_by=executor,
            question=f"Question {state}",
            status=state,
        )
    for state in conflict_statuses:
        ProjectConflict.objects.create(
            project=project,
            created_by=executor,
            title=f"Conflict {state}",
            status=state,
            resolution="Recorded resolution" if state == "resolved" else "",
        )

    context = get_specification_generation_context(project=project, actor=executor)
    prompt = build_specification_request(context)
    state = context["project_state"]

    assert {item["status"] for item in state["stages"]} == set(stage_statuses)
    assert {item["status"] for item in state["requirements"]} == set(
        requirement_statuses
    )
    assert {item["status"] for item in state["tasks"]} == set(task_statuses)
    assert {item["status"] for item in state["questions"]} == set(question_statuses)
    assert {item["status"] for item in state["conflicts"]} == set(conflict_statuses)
    resolved_conflict = next(
        item for item in state["conflicts"] if item["status"] == "resolved"
    )
    unresolved_conflict = next(
        item for item in state["conflicts"] if item["status"] == "unresolved"
    )
    dismissed_conflict = next(
        item for item in state["conflicts"] if item["status"] == "dismissed"
    )
    assert resolved_conflict == {
        "status": "resolved",
        "authority_note": "Resolved shared conflict; use only its recorded resolution.",
        "resolution": "Recorded resolution",
    }
    assert unresolved_conflict["title"] == "Conflict unresolved"
    assert "UNRESOLVED" in unresolved_conflict["authority_note"]
    assert dismissed_conflict["title"] == "Conflict dismissed"
    assert "DISMISSED" in dismissed_conflict["authority_note"]
    assert "DRAFT UNCONFIRMED" in prompt.user_input
    assert "REJECTED: exclude from current requirements" in prompt.user_input
    assert "CANCELLED: exclude from the current delivery plan" in prompt.user_input
    assert (
        "DISMISSED: neither conflicting claim was adopted as fact." in prompt.user_input
    )
    assert "CONFIRMED shared requirement." in prompt.user_input
    assert (
        "Resolved shared conflict; use only its recorded resolution."
        in prompt.user_input
    )
    assert (
        "Implementation task marked done; do not present as future work."
        in prompt.user_input
    )
    assert "Only confirmed requirements" in prompt.system_prompt
    assert "Specification project" not in prompt.user_input
    assert '"type": "website"' not in prompt.user_input


@pytest.mark.django_db
def test_unicode_context_over_budget_fails_before_router(monkeypatch, project_context):
    project, executor, *_ = project_context
    unicode_description = "😀" * 6_000
    assert len(unicode_description) == 6_000
    assert len(unicode_description.encode("utf-8")) == 24_000
    ProjectStage.objects.create(
        project=project,
        created_by=executor,
        name="Large Unicode context",
        description=unicode_description,
    )
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    provider_calls = []

    def unexpected_provider_call(**kwargs):
        provider_calls.append(kwargs)
        raise AssertionError("oversized context must not call the AI Router")

    monkeypatch.setattr(
        "apps.specifications.tasks.generate_text", unexpected_provider_call
    )
    from apps.specifications.tasks import generate_specification

    result = generate_specification.run(str(request.pk))

    request.refresh_from_db()
    assert result == "failed"
    assert provider_calls == []
    assert request.status == SpecificationGenerationStatus.FAILED
    assert request.error_code == "source_context_too_large"


@pytest.mark.django_db
def test_source_change_before_generation_skips_router_call(
    monkeypatch, project_context
):
    project, executor, *_ = project_context
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    OpenQuestion.objects.create(
        project=project,
        created_by=executor,
        question="Does this source change?",
    )

    def unexpected_provider_call(**kwargs):
        raise AssertionError("stale source context must not call the AI provider")

    monkeypatch.setattr(
        "apps.specifications.tasks.generate_text", unexpected_provider_call
    )
    from apps.specifications.tasks import generate_specification

    result = generate_specification.run(str(request.pk))

    request.refresh_from_db()
    assert result == "superseded"
    assert request.status == SpecificationGenerationStatus.SUPERSEDED
    assert request.error_code == "sources_changed"
    assert not Specification.objects.get(project=project).content


@pytest.mark.django_db
def test_source_change_after_prompt_build_but_before_router_skips_call(
    monkeypatch, project_context
):
    project, executor, *_ = project_context
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    from apps.specifications import tasks

    real_check = tasks.generation_request_matches_current_sources
    provider_calls = []

    def change_sources_at_provider_boundary(*, request_id, generation):
        OpenQuestion.objects.create(
            project=project,
            created_by=executor,
            question="Changed after prompt build and before provider call",
        )
        return real_check(request_id=request_id, generation=generation)

    monkeypatch.setattr(
        tasks,
        "generation_request_matches_current_sources",
        change_sources_at_provider_boundary,
    )
    monkeypatch.setattr(
        tasks,
        "generate_text",
        lambda **kwargs: provider_calls.append(kwargs),
    )

    result = tasks.generate_specification.run(str(request.pk))

    request.refresh_from_db()
    assert result == "superseded"
    assert request.status == SpecificationGenerationStatus.SUPERSEDED
    assert request.error_code == "sources_changed"
    assert provider_calls == []
    assert not Specification.objects.get(project=project).content


@pytest.mark.django_db
def test_source_change_during_generation_discards_provider_result(
    monkeypatch, project_context
):
    project, executor, *_ = project_context
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )

    def change_sources_then_generate(*, task_key, project_id, request):
        OpenQuestion.objects.create(
            project=project,
            created_by=executor,
            question="Changed while the model was running",
        )
        return SimpleNamespace(text="# Stale generated content")

    monkeypatch.setattr(
        "apps.specifications.tasks.generate_text", change_sources_then_generate
    )
    from apps.specifications.tasks import generate_specification

    result = generate_specification.run(str(request.pk))

    request.refresh_from_db()
    assert result == "superseded"
    assert request.status == SpecificationGenerationStatus.SUPERSEDED
    assert request.error_code == "sources_changed"
    assert not Specification.objects.get(project=project).content


@pytest.mark.django_db
def test_edit_wins_over_a_running_generation(project_context):
    project, executor, *_ = project_context
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    from apps.specifications.services import claim_generation_request

    state, generation, *_ = claim_generation_request(request_id=str(request.pk))
    saved = update_specification(
        project_id=project.pk,
        actor=executor,
        content="# Human edit",
        expected_version=1,
    )
    completed = complete_generation_request(
        request_id=request.pk,
        generation=generation,
        content="# Late generated text",
    )

    request.refresh_from_db()
    assert state == "claimed"
    assert saved.version == 2
    assert saved.content == "# Human edit"
    assert completed is False
    assert request.status == SpecificationGenerationStatus.SUPERSEDED
    assert Specification.objects.get(project=project).content == "# Human edit"


@pytest.mark.django_db
def test_router_failure_keeps_existing_draft_and_exposes_safe_error(
    monkeypatch, project_context
):
    project, executor, *_ = project_context
    update_specification(
        project_id=project.pk,
        actor=executor,
        content="# Existing draft",
        expected_version=1,
    )
    request = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )

    class RouterFailure(Exception):
        code = "provider_unavailable"

    def fail_generation(**kwargs):
        raise RouterFailure()

    monkeypatch.setattr("apps.specifications.tasks.generate_text", fail_generation)
    from apps.specifications.tasks import generate_specification

    result = generate_specification.run(str(request.pk))

    request.refresh_from_db()
    specification = Specification.objects.get(project=project)
    assert result == "failed"
    assert request.status == SpecificationGenerationStatus.FAILED
    assert request.error_code == "provider_unavailable"
    assert specification.content == "# Existing draft"
    assert specification.version == 2
    retry = queue_specification_generation(
        project_id=project.pk,
        actor=executor,
        idempotency_key=uuid4(),
    )
    assert retry.pk != request.pk
    assert retry.status == SpecificationGenerationStatus.QUEUED


@pytest.mark.django_db
def test_completed_project_is_readable_but_rejects_mutations(project_context):
    project, executor, customer, *_ = project_context
    project.status = "completed"
    project.save(update_fields=("status",))
    url = f"/api/v1/projects/{project.pk}/specification/"
    customer_read = _client(customer).get(url)
    edit = _client(executor).patch(
        url,
        {"content": "No longer writable", "version": 1},
        format="json",
    )
    generate = _client(executor).post(
        f"{url}generate/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )

    assert customer_read.status_code == 200
    assert edit.status_code == 409
    assert generate.status_code == 409


@pytest.mark.django_db
def test_archived_project_is_readable_but_rejects_mutations(project_context):
    from apps.projects.services import archive_project

    project, executor, customer, *_ = project_context
    archive_project(project_id=project.pk, actor=executor)
    url = f"/api/v1/projects/{project.pk}/specification/"
    customer_read = _client(customer).get(url)
    edit = _client(executor).patch(
        url,
        {"content": "No longer writable", "version": 1},
        format="json",
    )
    generate = _client(executor).post(
        f"{url}generate/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )

    assert customer_read.status_code == 200
    assert edit.status_code == 409
    assert generate.status_code == 409
