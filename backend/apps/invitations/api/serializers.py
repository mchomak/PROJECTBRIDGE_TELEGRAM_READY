from rest_framework import serializers

from apps.invitations.models import ProjectInvitation


class InvitationCreateSerializer(serializers.Serializer):
    invited_email = serializers.EmailField()


class InvitationResponseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True, format="hex_verbose")
    project_id = serializers.UUIDField(read_only=True, format="hex_verbose")

    class Meta:
        model = ProjectInvitation
        fields = (
            "id",
            "project_id",
            "invited_email",
            "status",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "created_at",
        )
        read_only_fields = fields


class InvitationListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = InvitationResponseSerializer(many=True)
