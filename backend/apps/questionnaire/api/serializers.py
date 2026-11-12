from collections.abc import Mapping

from rest_framework import serializers

from apps.projects.models import ProjectType
from apps.questionnaire.models import (
    QuestionnaireAnswer,
    QuestionnaireConflict,
    QuestionnaireConflictDecision,
    QuestionnaireSubmission,
)


class QuestionnaireAnswerResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionnaireAnswer
        fields = ("question_key", "value", "origin", "is_confirmed", "updated_at")
        read_only_fields = fields


class QuestionnaireSubmissionResponseSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    started_by_id = serializers.UUIDField(read_only=True)
    submitted_by_id = serializers.UUIDField(read_only=True, allow_null=True)
    supersedes_id = serializers.UUIDField(read_only=True, allow_null=True)
    answers = QuestionnaireAnswerResponseSerializer(many=True, read_only=True)

    class Meta:
        model = QuestionnaireSubmission
        fields = (
            "id",
            "project_id",
            "schema_key",
            "schema_version",
            "passport_version",
            "status",
            "started_by_id",
            "started_at",
            "submitted_by_id",
            "submitted_at",
            "supersedes_id",
            "answers",
        )
        read_only_fields = fields


class QuestionnaireQuestionSchemaSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    type = serializers.ChoiceField(
        choices=(
            "text",
            "textarea",
            "boolean",
            "select",
            "url",
            "date",
            "decimal",
            "currency",
            "string_list",
        )
    )
    required = serializers.BooleanField()
    min_length = serializers.IntegerField(required=False)
    max_length = serializers.IntegerField(required=False)
    min_items = serializers.IntegerField(required=False)
    max_items = serializers.IntegerField(required=False)
    minimum = serializers.CharField(required=False)
    maximum_digits = serializers.IntegerField(required=False)
    decimal_places = serializers.IntegerField(required=False)
    required_if_any = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    visible_if = serializers.JSONField(required=False)
    mapping = serializers.CharField(allow_null=True, required=False)
    options = serializers.ListField(child=serializers.JSONField(), required=False)


class QuestionnaireSchemaResponseSerializer(serializers.Serializer):
    schema_key = serializers.CharField()
    project_type = serializers.ChoiceField(choices=ProjectType.choices)
    version = serializers.IntegerField()
    questions = QuestionnaireQuestionSchemaSerializer(many=True)


class ProjectQuestionnaireResponseSerializer(serializers.Serializer):
    schema = QuestionnaireSchemaResponseSerializer()
    submission = QuestionnaireSubmissionResponseSerializer(allow_null=True)
    history = QuestionnaireSubmissionResponseSerializer(many=True)


class QuestionnaireConflictResponseSerializer(serializers.ModelSerializer):
    submission_id = serializers.UUIDField(read_only=True)
    question_key = serializers.CharField(source="answer.question_key", read_only=True)
    reviewed_by_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = QuestionnaireConflict
        fields = (
            "id",
            "submission_id",
            "question_key",
            "mapped_field",
            "passport_value",
            "answer_value",
            "status",
            "decision",
            "reviewed_by_id",
            "created_at",
            "resolved_at",
        )
        read_only_fields = fields


class StartQuestionnaireSubmissionSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping) and data:
            raise serializers.ValidationError(
                {"non_field_errors": ["No fields are accepted when starting a draft."]}
            )
        return super().to_internal_value(data)


class SaveQuestionnaireAnswersSerializer(serializers.Serializer):
    answers = serializers.DictField(child=serializers.JSONField())

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "Unknown questionnaire fields were provided."
                        ]
                    }
                )
        return super().to_internal_value(data)

    def validate_answers(self, value):
        if not value:
            raise serializers.ValidationError("At least one answer is required.")
        return value


class SubmitQuestionnaireSubmissionSerializer(serializers.Serializer):
    confirm_prefilled = serializers.BooleanField(required=False, default=False)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Unknown submission fields were provided."]}
                )
        return super().to_internal_value(data)


class RequestQuestionnaireCorrectionSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping) and data:
            raise serializers.ValidationError(
                {"non_field_errors": ["No fields are accepted for this action."]}
            )
        return super().to_internal_value(data)


class RefreshQuestionnairePassportVersionSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping) and data:
            raise serializers.ValidationError(
                {"non_field_errors": ["No fields are accepted for this action."]}
            )
        return super().to_internal_value(data)


class ResolveQuestionnaireConflictSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=QuestionnaireConflictDecision.choices)
    expected_passport_version = serializers.IntegerField(min_value=1)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Unknown conflict fields were provided."]}
                )
        return super().to_internal_value(data)
