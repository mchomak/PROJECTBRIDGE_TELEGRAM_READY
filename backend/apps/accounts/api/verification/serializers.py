from rest_framework import serializers


class ResendVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)


class ResendVerificationResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class ConfirmVerificationRequestSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False)


class ConfirmVerificationResponseSerializer(serializers.Serializer):
    email_verified = serializers.BooleanField()
    email_verified_at = serializers.DateTimeField()
