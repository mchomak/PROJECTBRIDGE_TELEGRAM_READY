from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
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
from apps.project_state.selectors import (
    get_project_conflicts_for_member,
    get_project_member_role,
    get_project_open_questions_for_member,
    get_project_requirements_for_member,
    get_project_stages_for_member,
    get_project_state_for_member,
    get_project_tasks_for_member,
    get_questionnaire_evidence_options_for_project,
)
from apps.project_state.services import (
    ProjectStateConflictError,
    ProjectStateNotFoundError,
    ProjectStatePermissionError,
    create_open_question,
    create_project_conflict,
    create_project_stage,
    create_requirement,
    create_task,
    update_open_question,
    update_project_conflict,
    update_project_stage,
    update_requirement,
    update_task,
)

from .serializers import (
    EvidenceOptionPageSerializer,
    EvidenceOptionResponseSerializer,
    OpenQuestionCreateSerializer,
    OpenQuestionPageSerializer,
    OpenQuestionPatchSerializer,
    OpenQuestionResponseSerializer,
    ProjectConflictCreateSerializer,
    ProjectConflictPageSerializer,
    ProjectConflictPatchSerializer,
    ProjectConflictResponseSerializer,
    ProjectStageCreateSerializer,
    ProjectStagePageSerializer,
    ProjectStagePatchSerializer,
    ProjectStageResponseSerializer,
    ProjectStateAggregateSerializer,
    RequirementCreateSerializer,
    RequirementPageSerializer,
    RequirementPatchSerializer,
    RequirementResponseSerializer,
    TaskCreateSerializer,
    TaskPageSerializer,
    TaskPatchSerializer,
    TaskResponseSerializer,
)


class ProjectStateTransitionConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The Project State change conflicts with its current state."
    default_code = "conflict"


def _translate_service_error(error):
    if isinstance(error, ProjectStateNotFoundError):
        raise NotFound(
            "The Project State record is unavailable to your account."
        ) from None
    if isinstance(error, ProjectStatePermissionError):
        raise PermissionDenied(
            "Only the project executor can change Project State."
        ) from None
    if isinstance(error, ProjectStateConflictError):
        raise ProjectStateTransitionConflict from None
    if isinstance(error, DjangoValidationError):
        detail = (
            error.message_dict
            if hasattr(error, "message_dict")
            else {"non_field_errors": error.messages}
        )
        raise ValidationError(detail) from None
    raise error


class ProjectStatePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ProjectStateAggregateView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["project_state"],
        operation_id="project_state_aggregate_retrieve",
        responses={
            200: ProjectStateAggregateSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        project = get_project_state_for_member(
            project_id=project_id, actor=request.user
        )
        if project is None:
            raise NotFound("Project State is unavailable to your account.")
        collection_names = {
            "stages": "project-stages",
            "requirements": "project-requirements",
            "tasks": "project-tasks",
            "open_questions": "project-open-questions",
            "conflicts": "project-conflicts",
            "evidence_options": "project-evidence-options",
        }
        collections = {
            name: request.build_absolute_uri(
                reverse(f"project_state:{route_name}", args=[project.pk])
            )
            for name, route_name in collection_names.items()
        }
        payload = {
            "project_id": project.pk,
            "counts": {
                "stages": project.stages_count,
                "requirements": project.requirements_count,
                "tasks": project.tasks_count,
                "open_questions": project.open_questions_count,
                "conflicts": project.conflicts_count,
            },
            "collections": collections,
        }
        return Response(ProjectStateAggregateSerializer(payload).data)


class ProjectStateCollectionView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]
    selector = None
    response_serializer_class = None
    create_serializer_class = None
    create_service = None

    def get(self, request, project_id):
        project = get_project_state_for_member(
            project_id=project_id, actor=request.user
        )
        if project is None:
            raise NotFound("Project State is unavailable to your account.")
        records = self.selector(project_id=project.pk, actor=request.user)
        paginator = ProjectStatePagination()
        page = paginator.paginate_queryset(records, request, view=self)
        serializer = self.response_serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, project_id):
        serializer = self.create_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record = self.create_service(
                project_id=project_id,
                actor=request.user,
                data=serializer.validated_data,
            )
        except (
            ProjectStateNotFoundError,
            ProjectStatePermissionError,
            ProjectStateConflictError,
            DjangoValidationError,
        ) as exc:
            _translate_service_error(exc)
        return Response(
            self.response_serializer_class(record).data,
            status=status.HTTP_201_CREATED,
        )


def _collection_schema(
    *, response_serializer, page_serializer, create_serializer, operation_prefix
):
    # Explicit schemas keep generated frontend types aligned with page results.
    return extend_schema_view(
        get=extend_schema(
            tags=["project_state"],
            operation_id=f"project_state_{operation_prefix}_list",
            parameters=[
                OpenApiParameter("page", OpenApiTypes.INT, required=False),
                OpenApiParameter("page_size", OpenApiTypes.INT, required=False),
            ],
            responses={
                200: page_serializer,
                401: ErrorEnvelopeSerializer,
                404: ErrorEnvelopeSerializer,
            },
        ),
        post=extend_schema(
            tags=["project_state"],
            operation_id=f"project_state_{operation_prefix}_create",
            request=create_serializer,
            responses={
                201: response_serializer,
                400: ErrorEnvelopeSerializer,
                401: ErrorEnvelopeSerializer,
                403: ErrorEnvelopeSerializer,
                404: ErrorEnvelopeSerializer,
                409: ErrorEnvelopeSerializer,
            },
        ),
    )


@_collection_schema(
    response_serializer=ProjectStageResponseSerializer,
    page_serializer=ProjectStagePageSerializer,
    create_serializer=ProjectStageCreateSerializer,
    operation_prefix="stages",
)
class ProjectStageCollectionView(ProjectStateCollectionView):
    selector = staticmethod(get_project_stages_for_member)
    response_serializer_class = ProjectStageResponseSerializer
    create_serializer_class = ProjectStageCreateSerializer
    create_service = staticmethod(create_project_stage)


@_collection_schema(
    response_serializer=RequirementResponseSerializer,
    page_serializer=RequirementPageSerializer,
    create_serializer=RequirementCreateSerializer,
    operation_prefix="requirements",
)
class RequirementCollectionView(ProjectStateCollectionView):
    selector = staticmethod(get_project_requirements_for_member)
    response_serializer_class = RequirementResponseSerializer
    create_serializer_class = RequirementCreateSerializer
    create_service = staticmethod(create_requirement)


@_collection_schema(
    response_serializer=TaskResponseSerializer,
    page_serializer=TaskPageSerializer,
    create_serializer=TaskCreateSerializer,
    operation_prefix="tasks",
)
class TaskCollectionView(ProjectStateCollectionView):
    selector = staticmethod(get_project_tasks_for_member)
    response_serializer_class = TaskResponseSerializer
    create_serializer_class = TaskCreateSerializer
    create_service = staticmethod(create_task)


@_collection_schema(
    response_serializer=OpenQuestionResponseSerializer,
    page_serializer=OpenQuestionPageSerializer,
    create_serializer=OpenQuestionCreateSerializer,
    operation_prefix="open_questions",
)
class OpenQuestionCollectionView(ProjectStateCollectionView):
    selector = staticmethod(get_project_open_questions_for_member)
    response_serializer_class = OpenQuestionResponseSerializer
    create_serializer_class = OpenQuestionCreateSerializer
    create_service = staticmethod(create_open_question)


@_collection_schema(
    response_serializer=ProjectConflictResponseSerializer,
    page_serializer=ProjectConflictPageSerializer,
    create_serializer=ProjectConflictCreateSerializer,
    operation_prefix="conflicts",
)
class ProjectConflictCollectionView(ProjectStateCollectionView):
    selector = staticmethod(get_project_conflicts_for_member)
    response_serializer_class = ProjectConflictResponseSerializer
    create_serializer_class = ProjectConflictCreateSerializer
    create_service = staticmethod(create_project_conflict)


class ProjectStateEvidenceOptionsView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["project_state"],
        operation_id="project_state_evidence_options_list",
        parameters=[
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False),
        ],
        responses={
            200: EvidenceOptionPageSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        role = get_project_member_role(project_id=project_id, actor=request.user)
        if role is None:
            raise NotFound("Project State is unavailable to your account.")
        if role != "executor":
            raise PermissionDenied("Only the executor can select conflict evidence.")
        options = get_questionnaire_evidence_options_for_project(project_id=project_id)
        paginator = ProjectStatePagination()
        page = paginator.paginate_queryset(options, request, view=self)
        return paginator.get_paginated_response(
            EvidenceOptionResponseSerializer(page, many=True).data
        )


class ProjectStateRecordView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]
    response_serializer_class = None
    patch_serializer_class = None
    update_service = None

    def patch(self, request, record_id):
        serializer = self.patch_serializer_class(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            record = self.update_service(
                record_id=record_id,
                actor=request.user,
                changes=serializer.validated_data,
            )
        except (
            ProjectStateNotFoundError,
            ProjectStatePermissionError,
            ProjectStateConflictError,
            DjangoValidationError,
        ) as exc:
            _translate_service_error(exc)
        return Response(self.response_serializer_class(record).data)


def _record_schema(*, response_serializer, patch_serializer, operation):
    return extend_schema_view(
        patch=extend_schema(
            tags=["project_state"],
            operation_id=f"project_state_{operation}_update",
            request=patch_serializer,
            responses={
                200: response_serializer,
                400: ErrorEnvelopeSerializer,
                401: ErrorEnvelopeSerializer,
                403: ErrorEnvelopeSerializer,
                404: ErrorEnvelopeSerializer,
                409: ErrorEnvelopeSerializer,
            },
        ),
    )


@_record_schema(
    response_serializer=ProjectStageResponseSerializer,
    patch_serializer=ProjectStagePatchSerializer,
    operation="stage",
)
class ProjectStageRecordView(ProjectStateRecordView):
    response_serializer_class = ProjectStageResponseSerializer
    patch_serializer_class = ProjectStagePatchSerializer
    update_service = staticmethod(update_project_stage)


@_record_schema(
    response_serializer=RequirementResponseSerializer,
    patch_serializer=RequirementPatchSerializer,
    operation="requirement",
)
class RequirementRecordView(ProjectStateRecordView):
    response_serializer_class = RequirementResponseSerializer
    patch_serializer_class = RequirementPatchSerializer
    update_service = staticmethod(update_requirement)


@_record_schema(
    response_serializer=TaskResponseSerializer,
    patch_serializer=TaskPatchSerializer,
    operation="task",
)
class TaskRecordView(ProjectStateRecordView):
    response_serializer_class = TaskResponseSerializer
    patch_serializer_class = TaskPatchSerializer
    update_service = staticmethod(update_task)


@_record_schema(
    response_serializer=OpenQuestionResponseSerializer,
    patch_serializer=OpenQuestionPatchSerializer,
    operation="open_question",
)
class OpenQuestionRecordView(ProjectStateRecordView):
    response_serializer_class = OpenQuestionResponseSerializer
    patch_serializer_class = OpenQuestionPatchSerializer
    update_service = staticmethod(update_open_question)


@_record_schema(
    response_serializer=ProjectConflictResponseSerializer,
    patch_serializer=ProjectConflictPatchSerializer,
    operation="conflict",
)
class ProjectConflictRecordView(ProjectStateRecordView):
    response_serializer_class = ProjectConflictResponseSerializer
    patch_serializer_class = ProjectConflictPatchSerializer
    update_service = staticmethod(update_project_conflict)
