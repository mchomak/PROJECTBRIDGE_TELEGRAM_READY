from datetime import timedelta
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.chat.models import Message
from apps.chat.services import send_message
from apps.projects.models import Project, ProjectMember, ProjectStatus
from apps.projects.services import archive_project, complete_project, create_project


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def chat_api_context():
    user_model = get_user_model()
    executor = user_model.objects.create_user(email="chat-api-executor@example.com")
    customer = user_model.objects.create_user(email="chat-api-customer@example.com")
    outsider = user_model.objects.create_user(email="chat-api-outsider@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Chat API project", "project_type": "other"},
    )
    Project.objects.filter(pk=project.pk).update(status=ProjectStatus.ACTIVE)
    project.refresh_from_db()
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )
    other_project = create_project(
        actor=outsider,
        data={"name": "Other chat API project", "project_type": "other"},
    )
    Project.objects.filter(pk=other_project.pk).update(status=ProjectStatus.ACTIVE)
    other_project.refresh_from_db()
    return project, executor, customer, outsider, other_project


def _messages_url(project):
    return f"/api/v1/projects/{project.pk}/messages/"


@pytest.mark.django_db
def test_both_project_roles_can_send_and_retry_idempotently(chat_api_context):
    project, executor, customer, _, _ = chat_api_context
    executor_client = _client(executor)
    customer_client = _client(customer)
    client_message_id = str(uuid4())
    body = {"client_message_id": client_message_id, "content": "The release is ready."}

    created = executor_client.post(_messages_url(project), body, format="json")
    replay = executor_client.post(_messages_url(project), body, format="json")
    conflict = executor_client.post(
        _messages_url(project),
        {**body, "content": "Different release note."},
        format="json",
    )
    history = customer_client.get(_messages_url(project))
    customer_send = customer_client.post(
        _messages_url(project),
        {"client_message_id": str(uuid4()), "content": "Thanks, I reviewed it."},
        format="json",
    )

    assert created.status_code == 201
    assert replay.status_code == 200
    assert replay.data["id"] == created.data["id"]
    assert conflict.status_code == 409
    assert history.status_code == 200
    assert history.data["results"][0]["id"] == created.data["id"]
    assert customer_send.status_code == 201
    assert Message.objects.filter(project=project).count() == 2


@pytest.mark.django_db
def test_message_replay_after_completion_and_archive_returns_original(chat_api_context):
    project, executor, _, _, _ = chat_api_context
    client = _client(executor)
    body = {
        "client_message_id": str(uuid4()),
        "content": "Persisted before completion.",
    }
    created = client.post(_messages_url(project), body, format="json")

    complete_project(project_id=project.pk, actor=executor)
    completed_replay = client.post(_messages_url(project), body, format="json")
    completed_conflict = client.post(
        _messages_url(project),
        {**body, "content": "Changed after completion."},
        format="json",
    )
    archive_project(project_id=project.pk, actor=executor)
    archived_replay = client.post(_messages_url(project), body, format="json")
    archived_conflict = client.post(
        _messages_url(project),
        {**body, "content": "Changed after archive."},
        format="json",
    )
    ProjectMember.objects.filter(project=project, user=executor).update(
        status="revoked"
    )
    revoked_member_replay = client.post(_messages_url(project), body, format="json")

    assert created.status_code == 201
    assert completed_replay.status_code == 200
    assert completed_replay.data["id"] == created.data["id"]
    assert completed_conflict.status_code == 409
    assert archived_replay.status_code == 200
    assert archived_replay.data["id"] == created.data["id"]
    assert archived_conflict.status_code == 409
    assert revoked_member_replay.status_code == 404
    assert Message.objects.filter(project=project).count() == 1


@pytest.mark.django_db
def test_history_is_member_scoped_and_read_only_project_statuses_keep_history(
    chat_api_context,
):
    project, executor, customer, outsider, other_project = chat_api_context
    send_message(
        project_id=project.pk,
        actor=executor,
        client_message_id=uuid4(),
        content="Persisted before completion.",
    )
    outsider_client = _client(outsider)
    customer_client = _client(customer)

    assert outsider_client.get(_messages_url(project)).status_code == 404
    assert (
        outsider_client.post(
            _messages_url(project),
            {"client_message_id": str(uuid4()), "content": "No access."},
            format="json",
        ).status_code
        == 404
    )
    assert customer_client.get(_messages_url(other_project)).status_code == 404
    assert APIClient().get(_messages_url(project)).status_code == 401

    complete_project(project_id=project.pk, actor=executor)
    completed_history = customer_client.get(_messages_url(project))
    completed_send = customer_client.post(
        _messages_url(project),
        {"client_message_id": str(uuid4()), "content": "Too late."},
        format="json",
    )
    archive_project(project_id=project.pk, actor=executor)
    archived_history = customer_client.get(_messages_url(project))
    executor_client = _client(executor)
    archived_send = executor_client.post(
        _messages_url(project),
        {"client_message_id": str(uuid4()), "content": "Still read only."},
        format="json",
    )

    assert completed_history.status_code == 200
    assert completed_send.status_code == 409
    assert archived_history.status_code == 200
    assert archived_send.status_code == 409


@pytest.mark.django_db
def test_cursor_history_defaults_to_50_and_caps_page_size_at_100(chat_api_context):
    project, executor, _, _, _ = chat_api_context
    start = timezone.now()
    Message.objects.bulk_create(
        [
            Message(
                project=project,
                sender=executor,
                content=f"Message {index}",
                client_message_id=uuid4(),
                created_at=start + timedelta(seconds=index),
            )
            for index in range(101)
        ]
    )
    client = _client(executor)

    default_page = client.get(_messages_url(project))
    maximum_page = client.get(f"{_messages_url(project)}?page_size=101")

    assert default_page.status_code == 200
    assert len(default_page.data["results"]) == 50
    assert default_page.data["next"] is not None
    assert maximum_page.status_code == 200
    assert len(maximum_page.data["results"]) == 100
    assert maximum_page.data["next"] is not None
    assert maximum_page.data["results"][0]["content"] == "Message 100"


@pytest.mark.django_db
def test_send_rejects_invalid_page_and_message_lengths(chat_api_context):
    project, executor, _, _, _ = chat_api_context
    client = _client(executor)

    invalid_page = client.get(f"{_messages_url(project)}?page_size=0")
    too_long = client.post(
        _messages_url(project),
        {"client_message_id": str(uuid4()), "content": "x" * 10_001},
        format="json",
    )
    maximum_length = client.post(
        _messages_url(project),
        {"client_message_id": str(uuid4()), "content": "x" * 10_000},
        format="json",
    )

    assert invalid_page.status_code == 400
    assert too_long.status_code == 400
    assert maximum_length.status_code == 201


@pytest.mark.django_db
def test_send_rate_limit_returns_429_without_persisting(chat_api_context):
    project, executor, _, _, _ = chat_api_context
    cache.clear()
    now = timezone.now()
    bucket = int(now.timestamp()) // 60
    cache.set(f"projectbridge:chat:send:{executor.pk}:{bucket}", 60, timeout=60)

    response = _client(executor).post(
        _messages_url(project),
        {"client_message_id": str(uuid4()), "content": "Rate limited message."},
        format="json",
    )

    assert response.status_code == 429
    assert Message.objects.filter(project=project).count() == 0
