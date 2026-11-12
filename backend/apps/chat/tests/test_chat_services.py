from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError

from apps.chat.models import Message
from apps.chat.services import (
    CHAT_SEND_LIMIT,
    ChatMessageConflictError,
    ChatMessageNotFoundError,
    ChatMessageRateLimitError,
    enforce_chat_send_rate_limit,
    list_messages,
    send_message,
)
from apps.common.models import ProjectAuditLog
from apps.projects.models import Project, ProjectMember, ProjectStatus
from apps.projects.services import create_project


@pytest.fixture
def chat_project_context():
    user_model = get_user_model()
    executor = user_model.objects.create_user(email="chat-executor@example.com")
    customer = user_model.objects.create_user(email="chat-customer@example.com")
    outsider = user_model.objects.create_user(email="chat-outsider@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Chat project", "project_type": "other"},
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
        data={"name": "Other chat project", "project_type": "other"},
    )
    Project.objects.filter(pk=other_project.pk).update(status=ProjectStatus.ACTIVE)
    other_project.refresh_from_db()
    return project, executor, customer, outsider, other_project


@pytest.mark.django_db
def test_send_message_persists_content_and_records_only_safe_audit_metadata(
    chat_project_context,
):
    project, executor, _, _, _ = chat_project_context
    client_message_id = uuid4()

    result = send_message(
        project_id=project.pk,
        actor=executor,
        client_message_id=client_message_id,
        content="Please review the updated scope.",
    )

    message = result.message
    assert result.created is True
    assert message.project_id == project.pk
    assert message.sender_id == executor.pk
    assert message.client_message_id == client_message_id
    assert message.content == "Please review the updated scope."
    audit = ProjectAuditLog.objects.get(
        project=project,
        action="chat.message_sent",
        target_id=str(message.pk),
    )
    assert audit.metadata == {"role": "executor"}
    assert message.content not in str(audit.metadata)


@pytest.mark.django_db
def test_send_message_retries_return_prior_row_and_conflicting_payloads_fail(
    chat_project_context,
):
    project, executor, _, _, _ = chat_project_context
    client_message_id = uuid4()
    first = send_message(
        project_id=project.pk,
        actor=executor,
        client_message_id=client_message_id,
        content="Same request",
    )
    replay = send_message(
        project_id=project.pk,
        actor=executor,
        client_message_id=client_message_id,
        content="Same request",
    )

    assert replay.created is False
    assert replay.message.pk == first.message.pk
    assert Message.objects.filter(project=project, sender=executor).count() == 1
    assert (
        ProjectAuditLog.objects.filter(
            project=project,
            action="chat.message_sent",
        ).count()
        == 1
    )

    with pytest.raises(ChatMessageConflictError):
        send_message(
            project_id=project.pk,
            actor=executor,
            client_message_id=client_message_id,
            content="Different request",
        )
    assert Message.objects.filter(project=project, sender=executor).count() == 1


@pytest.mark.django_db
def test_send_message_replay_survives_project_completion(chat_project_context):
    project, executor, _, _, _ = chat_project_context
    client_message_id = uuid4()
    first = send_message(
        project_id=project.pk,
        actor=executor,
        client_message_id=client_message_id,
        content="Persisted before completion",
    )
    Project.objects.filter(pk=project.pk).update(status=ProjectStatus.COMPLETED)

    replay = send_message(
        project_id=project.pk,
        actor=executor,
        client_message_id=client_message_id,
        content="Persisted before completion",
    )

    assert replay.created is False
    assert replay.message.pk == first.message.pk
    assert Message.objects.filter(project=project, sender=executor).count() == 1
    assert (
        ProjectAuditLog.objects.filter(
            project=project,
            action="chat.message_sent",
        ).count()
        == 1
    )
    with pytest.raises(ChatMessageConflictError):
        send_message(
            project_id=project.pk,
            actor=executor,
            client_message_id=client_message_id,
            content="Conflicting retry after completion",
        )


@pytest.mark.django_db
def test_send_message_rejects_content_over_10000_characters(chat_project_context):
    project, executor, _, _, _ = chat_project_context

    with pytest.raises(ValidationError):
        send_message(
            project_id=project.pk,
            actor=executor,
            client_message_id=uuid4(),
            content="x" * 10_001,
        )

    assert not Message.objects.filter(project=project).exists()


def test_chat_rate_limit_is_shared_per_user_and_resets_each_utc_minute():
    cache.clear()
    actor_id = uuid4()
    other_actor_id = uuid4()
    now = datetime(2026, 11, 12, 12, 34, 10, tzinfo=UTC)

    for _ in range(CHAT_SEND_LIMIT):
        enforce_chat_send_rate_limit(actor_id=actor_id, now=now)
    with pytest.raises(ChatMessageRateLimitError):
        enforce_chat_send_rate_limit(actor_id=actor_id, now=now)

    enforce_chat_send_rate_limit(actor_id=other_actor_id, now=now)
    enforce_chat_send_rate_limit(
        actor_id=actor_id,
        now=datetime(2026, 11, 12, 12, 35, 0, tzinfo=UTC),
    )


@pytest.mark.django_db
def test_message_history_is_member_scoped_and_cursor_pages_are_stable(
    chat_project_context,
):
    project, executor, customer, outsider, other_project = chat_project_context
    message_ids = [uuid4() for _ in range(3)]
    messages = [
        send_message(
            project_id=project.pk,
            actor=executor,
            client_message_id=client_message_id,
            content=f"Message {index}",
        ).message
        for index, client_message_id in enumerate(message_ids)
    ]
    created_at = datetime(2026, 11, 12, 12, 34, 10, tzinfo=UTC)
    for index, message in enumerate(messages):
        Message.objects.filter(pk=message.pk).update(
            created_at=created_at + timedelta(seconds=index)
        )
    page = list_messages(project_id=project.pk, actor=customer, limit=2)
    assert page.next_cursor is not None
    assert [message.pk for message in page.results] == [
        messages[2].pk,
        messages[1].pk,
    ]
    older_page = list_messages(
        project_id=project.pk,
        actor=customer,
        cursor=page.next_cursor,
        limit=2,
    )
    assert [message.pk for message in older_page.results] == [messages[0].pk]
    assert older_page.previous_cursor is not None
    assert [
        message.pk
        for message in list_messages(
            project_id=project.pk,
            actor=customer,
            cursor=older_page.previous_cursor,
            limit=2,
        ).results
    ] == [messages[2].pk, messages[1].pk]

    with pytest.raises(ChatMessageNotFoundError):
        list_messages(project_id=project.pk, actor=outsider)
    with pytest.raises(ChatMessageNotFoundError):
        list_messages(project_id=other_project.pk, actor=customer)


@pytest.mark.django_db
def test_message_cursor_pages_break_equal_timestamp_ties_by_id(chat_project_context):
    project, executor, customer, _, _ = chat_project_context
    created_at = datetime(2026, 11, 12, 12, 34, 10, tzinfo=UTC)
    messages = [
        Message(
            id=UUID(int=message_id),
            project=project,
            sender=executor,
            content=f"Message {message_id}",
            client_message_id=uuid4(),
            created_at=created_at,
        )
        for message_id in (1, 2, 3)
    ]
    Message.objects.bulk_create(messages)
    Message.objects.filter(pk__in=[message.pk for message in messages]).update(
        created_at=created_at
    )

    first_page = list_messages(project_id=project.pk, actor=customer, limit=2)
    second_page = list_messages(
        project_id=project.pk,
        actor=customer,
        cursor=first_page.next_cursor,
        limit=2,
    )

    assert [message.pk for message in first_page.results] == [
        UUID(int=3),
        UUID(int=2),
    ]
    assert [message.pk for message in second_page.results] == [UUID(int=1)]
