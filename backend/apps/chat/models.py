import uuid

from django.conf import settings
from django.db import models


class MessageType(models.TextChoices):
    TEXT = "text", "Text"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_project_messages",
    )
    content = models.TextField()
    message_type = models.CharField(
        max_length=16,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    client_message_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            models.Index(
                fields=("project", "created_at", "id"),
                name="chat_message_project_time_idx",
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("project", "sender", "client_message_id"),
                name="chat_message_client_id_unique",
            ),
        ]
