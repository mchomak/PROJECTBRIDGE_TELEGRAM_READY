from collections.abc import Mapping

from rest_framework import serializers

from apps.projects.models import Project, ProjectMember, ProjectType


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    project_type = serializers.ChoiceField(choices=ProjectType.choices)
    description = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Unknown project fields were provided."]}
                )
        return super().to_internal_value(data)


class ProjectMetadataUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    project_type = serializers.ChoiceField(
        choices=ProjectType.choices,
        required=False,
    )
    description = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Unknown project fields were provided."]}
                )
        return super().to_internal_value(data)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                {"non_field_errors": ["At least one metadata field is required."]}
            )
        return attrs


class ProjectResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "description",
            "project_type",
            "status",
            "created_at",
            "updated_at",
            "completed_at",
            "archived_at",
        )
        read_only_fields = fields


class ProjectListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ProjectResponseSerializer(many=True)


class ProjectMemberSummarySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="user_id", read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = ProjectMember
        fields = ("id", "user_id", "role", "joined_at", "first_name", "last_name")
        read_only_fields = fields
