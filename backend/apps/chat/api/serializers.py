from collections.abc import Mapping

from rest_framework import serializers

from apps.chat.models import Message


class StrictChatSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unexpected = set(data) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Unknown message fields were provided."]}
                )
        return super().to_internal_value(data)


class MessageCreateSerializer(StrictChatSerializer):
    client_message_id = serializers.UUIDField()
    content = serializers.CharField(max_length=10_000, trim_whitespace=True)


class MessageResponseSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    sender_id = serializers.UUIDField(read_only=True)
    id = serializers.UUIDField(read_only=True)
    client_message_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "project_id",
            "sender_id",
            "content",
            "message_type",
            "client_message_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class MessagePageResponseSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = MessageResponseSerializer(many=True)
