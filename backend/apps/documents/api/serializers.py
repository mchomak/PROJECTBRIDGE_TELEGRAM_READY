from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.documents.models import (
    Document,
    DocumentLifecycleAction,
    DocumentLifecycleApproval,
    DocumentLifecycleDecision,
    DocumentLifecycleRequest,
)


class DocumentLifecycleActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=DocumentLifecycleAction.choices)


class EmptyLifecycleActionSerializer(serializers.Serializer):
    pass


class DocumentLifecycleApprovalResponseSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True, format="hex_verbose")

    class Meta:
        model = DocumentLifecycleApproval
        fields = ("user_id", "decision", "decided_at")
        read_only_fields = fields


class DocumentLifecycleRequestResponseSerializer(serializers.ModelSerializer):
    document_id = serializers.UUIDField(read_only=True, format="hex_verbose")
    initiated_by_id = serializers.UUIDField(read_only=True, format="hex_verbose")
    approvals = DocumentLifecycleApprovalResponseSerializer(many=True, read_only=True)
    viewer_decision = serializers.SerializerMethodField()

    class Meta:
        model = DocumentLifecycleRequest
        fields = (
            "id",
            "document_id",
            "action",
            "initiated_by_id",
            "status",
            "approvals",
            "viewer_decision",
            "deletion_after",
            "created_at",
            "completed_at",
        )
        read_only_fields = fields

    @extend_schema_field(
        serializers.ChoiceField(
            choices=DocumentLifecycleDecision.choices,
            allow_null=True,
        )
    )
    def get_viewer_decision(self, obj) -> str | None:
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        approval = obj.approvals.filter(user_id=request.user.pk).first()
        return approval.decision if approval is not None else None


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)


class DocumentResponseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True, format="hex_verbose")
    project_id = serializers.UUIDField(read_only=True, format="hex_verbose")
    uploaded_by_id = serializers.UUIDField(read_only=True, format="hex_verbose")
    lifecycle_request = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "project_id",
            "uploaded_by_id",
            "original_filename",
            "mime_type",
            "file_size",
            "checksum_sha256",
            "lifecycle_status",
            "processing_status",
            "created_at",
            "archived_at",
            "deleted_at",
            "lifecycle_request",
        )
        read_only_fields = fields

    @extend_schema_field(DocumentLifecycleRequestResponseSerializer(allow_null=True))
    def get_lifecycle_request(self, obj) -> dict | None:
        current_request_status = {
            "archive_pending": ("archive", "pending"),
            "archived": ("permanent_delete", "pending"),
            "deletion_pending": ("permanent_delete", "approved"),
        }.get(obj.lifecycle_status)
        if current_request_status is None:
            return None

        action, status = current_request_status
        lifecycle_request = next(
            (
                request
                for request in obj.lifecycle_requests.all()
                if request.action == action and request.status == status
            ),
            None,
        )
        if lifecycle_request is None:
            return None
        return DocumentLifecycleRequestResponseSerializer(
            lifecycle_request,
            context=self.context,
        ).data


class DocumentListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = DocumentResponseSerializer(many=True)
