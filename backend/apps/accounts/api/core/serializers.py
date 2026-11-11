from django.contrib.auth import get_user_model
from rest_framework import serializers


class UserSummarySerializer(serializers.ModelSerializer):
    email_verified = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "email_verified",
            "email_verified_at",
        )
        read_only_fields = fields

    def get_email_verified(self, user) -> bool:
        return user.email_verified_at is not None


class CredentialsSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class CsrfTokenSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()


class ErrorEnvelopeSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    errors = serializers.JSONField(allow_null=True, required=False)
    request_id = serializers.UUIDField()
