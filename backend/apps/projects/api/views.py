from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.accounts.api.core.permissions import (
    CsrfSanitizingAPIView,
    RequireAuthenticatedUser,
    RequireCsrfForUnsafeRequests,
)
from apps.accounts.api.core.serializers import ErrorEnvelopeSerializer
from apps.projects.models import ProjectStatus
from apps.projects.selectors import (
    get_active_project_members,
    get_project_for_member,
    get_projects_for_member,
)
from apps.projects.services import (
    ProjectNotFoundError,
    ProjectPermissionError,
    ProjectStateConflictError,
    create_project,
    update_project_metadata,
)

from .serializers import (
    ProjectCreateSerializer,
    ProjectListResponseSerializer,
    ProjectMemberSummarySerializer,
    ProjectMetadataUpdateSerializer,
    ProjectResponseSerializer,
)


class ProjectPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ProjectMetadataConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Project metadata cannot be changed in its current state."
    default_code = "conflict"


class ProjectListCreateView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["projects"],
        operation_id="projects_list",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                enum=[ProjectStatus.ARCHIVED],
                required=False,
            ),
            OpenApiParameter(name="page", type=OpenApiTypes.INT, required=False),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                required=False,
            ),
        ],
        responses={
            200: ProjectListResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request):
        status_filter = request.query_params.get("status")
        if status_filter is not None and status_filter != ProjectStatus.ARCHIVED:
            raise ValidationError({"status": ["Select a valid choice."]})

        projects = get_projects_for_member(user=request.user, status=status_filter)
        paginator = ProjectPagination()
        page = paginator.paginate_queryset(projects, request, view=self)
        serializer = ProjectResponseSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["projects"],
        operation_id="projects_create",
        request=ProjectCreateSerializer,
        responses={
            201: ProjectResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request):
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user.email_verified_at is None:
            raise PermissionDenied("Email verification is required to create projects.")

        try:
            project = create_project(actor=request.user, data=serializer.validated_data)
        except DjangoValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, "message_dict")
                else {"non_field_errors": exc.messages}
            )
            raise ValidationError(detail) from exc

        return Response(
            ProjectResponseSerializer(project).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["projects"],
        operation_id="projects_retrieve",
        responses={
            200: ProjectResponseSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        project = get_project_for_member(project_id=project_id, user=request.user)
        if project is None:
            raise NotFound("Project not found.")
        return Response(ProjectResponseSerializer(project).data)

    @extend_schema(
        tags=["projects"],
        operation_id="projects_update_metadata",
        request=ProjectMetadataUpdateSerializer,
        responses={
            200: ProjectResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
        },
    )
    def patch(self, request, project_id):
        serializer = ProjectMetadataUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            project = update_project_metadata(
                project_id=project_id,
                actor=request.user,
                changes=serializer.validated_data,
            )
        except DjangoValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, "message_dict")
                else {"non_field_errors": exc.messages}
            )
            raise ValidationError(detail) from exc
        except ProjectNotFoundError as exc:
            raise NotFound("Project not found.") from exc
        except ProjectPermissionError as exc:
            raise PermissionDenied(
                "Only an executor can update project metadata."
            ) from exc
        except ProjectStateConflictError as exc:
            raise ProjectMetadataConflict() from exc

        return Response(ProjectResponseSerializer(project).data)


class ProjectMemberListView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["projects"],
        operation_id="projects_members_list",
        responses={
            200: ProjectMemberSummarySerializer(many=True),
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        project = get_project_for_member(project_id=project_id, user=request.user)
        if project is None:
            raise NotFound("Project not found.")
        members = get_active_project_members(project_id=project.pk)
        return Response(ProjectMemberSummarySerializer(members, many=True).data)
