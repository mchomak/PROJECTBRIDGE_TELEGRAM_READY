from collections.abc import Mapping

from rest_framework import serializers

from apps.projects.models import Project, ProjectMember, ProjectPassport, ProjectType


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


class ProjectPassportResponseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True, format="hex_verbose")
    project_id = serializers.UUIDField(read_only=True, format="hex_verbose")

    class Meta:
        model = ProjectPassport
        fields = (
            "id",
            "project_id",
            "goal",
            "target_audience",
            "expected_result",
            "functional_scope",
            "integrations",
            "constraints",
            "deadline",
            "budget_min",
            "budget_max",
            "currency",
            "additional_data",
            "version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProjectPassportUpdateSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    goal = serializers.CharField(required=False, allow_blank=True)
    target_audience = serializers.CharField(required=False, allow_blank=True)
    expected_result = serializers.CharField(required=False, allow_blank=True)
    functional_scope = serializers.JSONField(required=False)
    integrations = serializers.JSONField(required=False)
    constraints = serializers.JSONField(required=False)
    deadline = serializers.DateField(required=False, allow_null=True)
    budget_min = serializers.DecimalField(
        max_digits=30,
        decimal_places=10,
        required=False,
        allow_null=True,
    )
    budget_max = serializers.DecimalField(
        max_digits=30,
        decimal_places=10,
        required=False,
        allow_null=True,
    )
    currency = serializers.CharField(max_length=3, required=False, allow_null=True)
    additional_data = serializers.JSONField(required=False)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Unknown passport fields were provided."]}
                )
        return super().to_internal_value(data)

    def validate_currency(self, value):
        if value is None:
            return None
        if len(value) != 3 or not value.isascii() or not value.isalpha():
            raise serializers.ValidationError(
                "Currency must contain exactly three ASCII letters."
            )
        return value.upper()

    def validate(self, attrs):
        if not set(attrs) - {"version"}:
            raise serializers.ValidationError(
                {"non_field_errors": ["At least one passport field is required."]}
            )
        return attrs


class ProjectPassportPatchSchemaSerializer(ProjectPassportUpdateSerializer):
    """Keep the version required in drf-spectacular's PATCH request schema.

    drf-spectacular marks every serializer partial for PATCH operations. The
    passport uses optional business fields but requires the optimistic version,
    so the schema-only serializer ignores that automatic partial flag.
    """

    @property
    def partial(self):
        return False

    @partial.setter
    def partial(self, value):
        del value
