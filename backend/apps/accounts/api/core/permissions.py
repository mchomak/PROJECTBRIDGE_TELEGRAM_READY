from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.views import APIView


class CsrfSanitizingAPIView(APIView):
    def perform_authentication(self, request):
        try:
            super().perform_authentication(request)
        except PermissionDenied:
            raise PermissionDenied("CSRF verification failed.") from None


class Unauthenticated(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication is required."
    default_code = "unauthenticated"


class RequireAuthenticatedUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise Unauthenticated()
        return True


class RequireCsrfForUnsafeRequests(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        try:
            SessionAuthentication().enforce_csrf(request)
        except PermissionDenied:
            raise PermissionDenied("CSRF verification failed.") from None
        return True
