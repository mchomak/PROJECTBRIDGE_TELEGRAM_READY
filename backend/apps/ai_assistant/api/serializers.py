from collections.abc import Mapping

from rest_framework import serializers

from apps.ai_assistant.models import (
    AIAnalysisRequest,
    AIAnalysisRun,
    AIProposal,
    AIProposalEvidence,
)


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unexpected = set(data) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Unknown AI workspace fields were provided."]}
                )
        return super().to_internal_value(data)


class EmptyRequestSerializer(StrictSerializer):
    pass


class ApplyEditedProposalSerializer(StrictSerializer):
    final_payload = serializers.JSONField()

    def validate_final_payload(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Provide a structured object.")
        return value


class AIAnalysisRunSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysisRun
        fields = (
            "id",
            "task_key",
            "trigger_type",
            "provider_key",
            "model_name",
            "profile_version",
            "status",
            "input_tokens",
            "output_tokens",
            "estimated_cost",
            "error_code",
            "attempt_count",
            "started_at",
            "completed_at",
        )
        read_only_fields = fields


class AIAnalysisRequestSerializer(serializers.ModelSerializer):
    run = AIAnalysisRunSummarySerializer(read_only=True, allow_null=True)

    class Meta:
        model = AIAnalysisRequest
        fields = (
            "id",
            "status",
            "result_count",
            "error_code",
            "created_at",
            "started_at",
            "completed_at",
            "run",
        )
        read_only_fields = fields


class AIProposalEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIProposalEvidence
        fields = ("id", "source_type", "source_id", "excerpt", "metadata")
        read_only_fields = fields


class AIProposalSerializer(serializers.ModelSerializer):
    analysis_run_id = serializers.UUIDField(read_only=True)
    evidence = AIProposalEvidenceSerializer(
        source="evidence_links", many=True, read_only=True
    )

    class Meta:
        model = AIProposal
        fields = (
            "id",
            "analysis_run_id",
            "proposal_type",
            "title",
            "description",
            "rationale",
            "proposed_payload",
            "final_payload",
            "status",
            "reviewed_by_id",
            "reviewed_at",
            "applied_at",
            "created_at",
            "evidence",
        )
        read_only_fields = fields


class AIAnalysisRequestPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AIAnalysisRequestSerializer(many=True)


class AIProposalPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AIProposalSerializer(many=True)
