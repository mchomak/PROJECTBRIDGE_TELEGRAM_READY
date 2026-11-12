from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.common.services import record_project_action
from apps.projects.models import (
    Project,
    ProjectMember,
    ProjectMemberStatus,
    ProjectStatus,
)

from .models import Message
from .selectors import get_messages_for_member

MAX_MESSAGE_LENGTH = 10_000
CHAT_SEND_LIMIT = 60
CHAT_SEND_WINDOW_SECONDS = 60
MESSAGE_CURSOR_SALT = "apps.chat.message_cursor"


@dataclass(frozen=True)
class MessagePage:
    results: list[Message]
    next_cursor: str | None
    previous_cursor: str | None


@dataclass(frozen=True)
class SendMessageResult:
    message: Message
    created: bool


class ChatMessageNotFoundError(Exception):
    """The project is unavailable to the active member."""


class ChatMessageConflictError(Exception):
    """The message ID or project state conflicts with the request."""


class ChatMessageRateLimitError(Exception):
    """The user exceeded the project chat send rate limit."""


def _normalize_message_content(content):
    if not isinstance(content, str):
        raise ValidationError({"content": "Enter a valid message."})
    normalized = content.strip()
    if not normalized:
        raise ValidationError({"content": "Message content cannot be blank."})
    if len(normalized) > MAX_MESSAGE_LENGTH:
        raise ValidationError(
            {
                "content": (
                    f"Message content must not exceed {MAX_MESSAGE_LENGTH} characters."
                )
            }
        )
    return normalized


def enforce_chat_send_rate_limit(*, actor_id, now=None):
    """Count sends in the shared user-scoped Redis bucket for REST and WebSocket."""
    now = now or timezone.now()
    timestamp = int(now.timestamp())
    bucket = timestamp // CHAT_SEND_WINDOW_SECONDS
    remaining = CHAT_SEND_WINDOW_SECONDS - timestamp % CHAT_SEND_WINDOW_SECONDS
    cache_key = f"projectbridge:chat:send:{actor_id}:{bucket}"

    if cache.add(cache_key, 1, timeout=remaining):
        count = 1
    else:
        try:
            count = cache.incr(cache_key)
        except ValueError:
            if cache.add(cache_key, 1, timeout=remaining):
                count = 1
            else:
                count = cache.incr(cache_key)

    if count > CHAT_SEND_LIMIT:
        raise ChatMessageRateLimitError


def _cursor_for(*, message, direction):
    return signing.dumps(
        {
            "created_at": message.created_at.isoformat(),
            "direction": direction,
            "id": str(message.pk),
        },
        salt=MESSAGE_CURSOR_SALT,
    )


def _position_from_cursor(cursor):
    if cursor is None:
        return None
    try:
        value = signing.loads(cursor, salt=MESSAGE_CURSOR_SALT)
        if set(value) != {"created_at", "direction", "id"}:
            raise ValueError
        created_at = datetime.fromisoformat(value["created_at"])
        message_id = UUID(value["id"])
        direction = value["direction"]
        if not timezone.is_aware(created_at) or direction not in {"older", "newer"}:
            raise ValueError
        return created_at, message_id, direction
    except (signing.BadSignature, TypeError, ValueError, KeyError):
        raise ValidationError({"cursor": "The message cursor is invalid."}) from None


def list_messages(*, project_id, actor, cursor=None, limit=50):
    """Return a stable, signed cursor page of newest-first project history."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValidationError({"page_size": "Page size must be between 1 and 100."})
    limit = min(limit, 100)
    if not ProjectMember.objects.filter(
        project_id=project_id,
        user=actor,
        status=ProjectMemberStatus.ACTIVE,
    ).exists():
        raise ChatMessageNotFoundError

    messages = get_messages_for_member(project_id=project_id, actor=actor)
    position = _position_from_cursor(cursor)
    direction = "older"
    if position is not None:
        created_at, message_id, direction = position
        if direction == "older":
            messages = messages.filter(
                Q(created_at__lt=created_at)
                | Q(created_at=created_at, id__lt=message_id)
            ).order_by("-created_at", "-id")
        else:
            messages = messages.filter(
                Q(created_at__gt=created_at)
                | Q(created_at=created_at, id__gt=message_id)
            ).order_by("created_at", "id")
    elif cursor is not None:
        raise ValidationError({"cursor": "The message cursor is invalid."})
    else:
        messages = messages.order_by("-created_at", "-id")

    rows = list(messages[: limit + 1])
    has_more = len(rows) > limit
    rows = rows[:limit]
    if direction == "newer":
        rows.reverse()

    if direction == "newer":
        next_cursor = (
            _cursor_for(message=rows[-1], direction="older")
            if position is not None and rows
            else None
        )
        previous_cursor = (
            _cursor_for(message=rows[0], direction="newer")
            if has_more and rows
            else None
        )
    else:
        next_cursor = (
            _cursor_for(message=rows[-1], direction="older")
            if has_more and rows
            else None
        )
        previous_cursor = (
            _cursor_for(message=rows[0], direction="newer")
            if position is not None and rows
            else None
        )
    return MessagePage(
        results=rows,
        next_cursor=next_cursor,
        previous_cursor=previous_cursor,
    )


@transaction.atomic
def send_message(*, project_id, actor, client_message_id, content):
    normalized_content = _normalize_message_content(content)
    project = Project.objects.select_for_update().filter(pk=project_id).first()
    if project is None:
        raise ChatMessageNotFoundError

    role = (
        ProjectMember.objects.filter(
            project=project,
            user=actor,
            status=ProjectMemberStatus.ACTIVE,
        )
        .values_list("role", flat=True)
        .first()
    )
    if role is None:
        raise ChatMessageNotFoundError

    existing = Message.objects.filter(
        project=project,
        sender=actor,
        client_message_id=client_message_id,
    ).first()
    if existing is not None:
        if existing.content != normalized_content:
            raise ChatMessageConflictError
        return SendMessageResult(message=existing, created=False)

    if project.status != ProjectStatus.ACTIVE:
        raise ChatMessageConflictError

    enforce_chat_send_rate_limit(actor_id=actor.pk)
    message = Message.objects.create(
        project=project,
        sender=actor,
        client_message_id=client_message_id,
        content=normalized_content,
    )
    record_project_action(
        project_id=project.pk,
        actor_id=actor.pk,
        action="chat.message_sent",
        target_type="message",
        target_id=message.pk,
        metadata={"role": role},
    )
    return SendMessageResult(message=message, created=True)
