from collections.abc import Mapping

from rest_framework import serializers

from apps.project_state.models import (
    Evidence,
    OpenQuestion,
    OpenQuestionStatus,
    ProjectConflict,
    ProjectConflictStatus,
    ProjectStage,
    ProjectStageStatus,
    Requirement,
    RequirementStatus,
    Task,
    TaskStatus,
)


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unexpected = set(data) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Unknown Project State fields were provided."
                        ]
                    }
                )
        return super().to_internal_value(data)


class EvidenceResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = (
            "id",
            "source_type",
            "source_id",
            "excerpt",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class ProjectStageResponseSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    created_by_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ProjectStage
        fields = (
            "id",
            "project_id",
            "name",
            "description",
            "position",
            "status",
            "start_date",
            "due_date",
            "created_by_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RequirementResponseSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    created_by_id = serializers.UUIDField(read_only=True)
    confirmed_by_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = Requirement
        fields = (
            "id",
            "project_id",
            "title",
            "description",
            "status",
            "created_by_id",
            "confirmed_by_id",
            "confirmed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TaskResponseSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    created_by_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "project_id",
            "stage_id",
            "title",
            "description",
            "status",
            "assignee_id",
            "due_date",
            "created_by_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OpenQuestionResponseSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    created_by_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = OpenQuestion
        fields = (
            "id",
            "project_id",
            "question",
            "answer",
            "status",
            "created_by_id",
            "resolved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProjectConflictResponseSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    created_by_id = serializers.UUIDField(read_only=True)
    resolved_by_id = serializers.UUIDField(read_only=True, allow_null=True)
    evidence = EvidenceResponseSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectConflict
        fields = (
            "id",
            "project_id",
            "title",
            "description",
            "status",
            "resolution",
            "resolved_by_id",
            "resolved_at",
            "evidence",
            "created_by_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProjectStateCountsSerializer(serializers.Serializer):
    stages = serializers.IntegerField()
    requirements = serializers.IntegerField()
    tasks = serializers.IntegerField()
    open_questions = serializers.IntegerField()
    conflicts = serializers.IntegerField()


class ProjectStateCollectionsSerializer(serializers.Serializer):
    stages = serializers.CharField()
    requirements = serializers.CharField()
    tasks = serializers.CharField()
    open_questions = serializers.CharField()
    conflicts = serializers.CharField()
    evidence_options = serializers.CharField()


class ProjectStateAggregateSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    counts = ProjectStateCountsSerializer()
    collections = ProjectStateCollectionsSerializer()


class ProjectStatePageBaseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)


class ProjectStagePageSerializer(ProjectStatePageBaseSerializer):
    results = ProjectStageResponseSerializer(many=True)


class RequirementPageSerializer(ProjectStatePageBaseSerializer):
    results = RequirementResponseSerializer(many=True)


class TaskPageSerializer(ProjectStatePageBaseSerializer):
    results = TaskResponseSerializer(many=True)


class OpenQuestionPageSerializer(ProjectStatePageBaseSerializer):
    results = OpenQuestionResponseSerializer(many=True)


class ProjectConflictPageSerializer(ProjectStatePageBaseSerializer):
    results = ProjectConflictResponseSerializer(many=True)


class EvidenceOptionResponseSerializer(serializers.Serializer):
    source_type = serializers.SerializerMethodField()
    source_id = serializers.UUIDField(source="pk")
    question_key = serializers.CharField()
    value = serializers.JSONField()
    schema_key = serializers.CharField(source="submission.schema_key")
    schema_version = serializers.IntegerField(source="submission.schema_version")
    submitted_at = serializers.DateTimeField(source="submission.submitted_at")

    def get_source_type(self, _answer) -> str:
        return "questionnaire_answer"


class EvidenceOptionPageSerializer(ProjectStatePageBaseSerializer):
    results = EvidenceOptionResponseSerializer(many=True)


class ProjectStageCreateSerializer(StrictSerializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    position = serializers.IntegerField(required=False, min_value=0, default=0)
    start_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)


class ProjectStagePatchSerializer(StrictSerializer):
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    position = serializers.IntegerField(required=False, min_value=0)
    status = serializers.ChoiceField(choices=ProjectStageStatus.choices, required=False)
    start_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)


class RequirementCreateSerializer(StrictSerializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")


class RequirementPatchSerializer(StrictSerializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=RequirementStatus.choices, required=False)


class TaskCreateSerializer(StrictSerializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    stage_id = serializers.UUIDField(required=False, allow_null=True)
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)


class TaskPatchSerializer(StrictSerializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    stage_id = serializers.UUIDField(required=False, allow_null=True)
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=TaskStatus.choices, required=False)


class OpenQuestionCreateSerializer(StrictSerializer):
    question = serializers.CharField()
    answer = serializers.CharField(required=False, allow_blank=True, default="")


class OpenQuestionPatchSerializer(StrictSerializer):
    question = serializers.CharField(required=False)
    answer = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=OpenQuestionStatus.choices, required=False)


class EvidenceReferenceSerializer(StrictSerializer):
    source_type = serializers.ChoiceField(choices=("questionnaire_answer",))
    source_id = serializers.UUIDField()


class ProjectConflictCreateSerializer(StrictSerializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    evidence_refs = EvidenceReferenceSerializer(many=True, min_length=2)


class ProjectConflictPatchSerializer(StrictSerializer):
    status = serializers.ChoiceField(
        choices=ProjectConflictStatus.choices, required=False
    )
    resolution = serializers.CharField(required=False, allow_blank=True)
