from rest_framework import serializers

from apps.documents.models import Document


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)


class DocumentResponseSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True, format="hex_verbose")
    project_id = serializers.UUIDField(read_only=True, format="hex_verbose")
    uploaded_by_id = serializers.UUIDField(read_only=True, format="hex_verbose")

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
        )
        read_only_fields = fields


class DocumentListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = DocumentResponseSerializer(many=True)
