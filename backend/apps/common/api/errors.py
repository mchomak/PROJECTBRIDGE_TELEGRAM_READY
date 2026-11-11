import logging
from uuid import uuid4

from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

logger = logging.getLogger(__name__)

_ERROR_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "throttled",
}


def _error_envelope(*, code, detail, errors=None):
    return {
        "code": code,
        "detail": detail,
        "errors": errors,
        "request_id": str(uuid4()),
    }


def _response_detail(data):
    if isinstance(data, dict) and "detail" in data:
        return str(data["detail"])
    return "The request could not be completed."


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        set_rollback()
        logger.error("Unhandled API exception: %s", type(exc).__name__)
        return Response(
            _error_envelope(
                code="internal_error",
                detail="An unexpected error occurred.",
            ),
            status=500,
        )

    if isinstance(exc, ValidationError):
        code = "validation_error"
        detail = "Request validation failed."
        errors = response.data
    else:
        code = _ERROR_CODES.get(response.status_code, "request_failed")
        detail = _response_detail(response.data)
        errors = None

    response.data = _error_envelope(code=code, detail=detail, errors=errors)
    return response


def csrf_failure(request, reason):
    return JsonResponse(
        _error_envelope(
            code="csrf_failed",
            detail="CSRF verification failed.",
        ),
        status=403,
    )
