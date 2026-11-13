from collections.abc import Mapping

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from ..models import Specification, SpecificationGenerationRequest
from ..services import MAX_MARKDOWN_LENGTH


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unexpected = set(data) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Unknown specification fields were provided."
                        ]
                    }
                )
        return super().to_internal_value(data)


class EmptyRequestSerializer(StrictSerializer):
    pass


class SpecificationPatchSerializer(StrictSerializer):
    content = serializers.CharField(
        allow_blank=True,
        max_length=MAX_MARKDOWN_LENGTH,
        trim_whitespace=False,
    )
    version = serializers.IntegerField(min_value=1)


class SpecificationPatchSchemaSerializer(SpecificationPatchSerializer):
    """Keep all optimistic-patch fields required in the PATCH OpenAPI schema."""

    @property
    def partial(self):
        return False

    @partial.setter
    def partial(self, value):
        del value


class SpecificationGenerationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecificationGenerationRequest
        fields = (
            "id",
            "status",
            "expected_version",
            "error_code",
            "created_at",
            "started_at",
            "completed_at",
        )
        read_only_fields = fields


class SpecificationSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    updated_by_id = serializers.UUIDField(read_only=True)
    generation = serializers.SerializerMethodField()

    class Meta:
        model = Specification
        fields = (
            "id",
            "project_id",
            "content",
            "status",
            "updated_by_id",
            "version",
            "created_at",
            "updated_at",
            "generation",
        )
        read_only_fields = fields

    @extend_schema_field(SpecificationGenerationRequestSerializer(allow_null=True))
    def get_generation(self, instance):
        generation = self.context.get("generation")
        if generation is None:
            return None
        return SpecificationGenerationRequestSerializer(generation).data
