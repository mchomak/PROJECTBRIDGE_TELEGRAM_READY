from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .checks import check_readiness

health_response = inline_serializer(
    name="HealthResponse",
    fields={
        "status": serializers.ChoiceField(choices=["ok", "unavailable"]),
        "dependencies": serializers.DictField(
            child=serializers.ChoiceField(choices=["ok", "unavailable"])
        ),
    },
)


@extend_schema(
    tags=["health"],
    operation_id="health_check",
    summary="Check backend readiness",
    responses={
        200: health_response,
        503: OpenApiResponse(
            response=health_response,
            description="A required backend dependency is unavailable.",
        ),
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    dependencies = check_readiness()
    all_available = all(dependencies.values())
    status = "ok" if all_available else "unavailable"
    response = {
        "status": status,
        "dependencies": {
            name: "ok" if available else "unavailable"
            for name, available in dependencies.items()
        },
    }
    return Response(response, status=200 if all_available else 503)
