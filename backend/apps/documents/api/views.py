from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.api.core.permissions import (
    CsrfSanitizingAPIView,
    RequireAuthenticatedUser,
    RequireCsrfForUnsafeRequests,
)
from apps.accounts.api.core.serializers import ErrorEnvelopeSerializer
from apps.documents.services import (
    DocumentNotFoundError,
    DocumentStateConflictError,
    DocumentTooLargeError,
    UnsupportedDocumentError,
    get_document,
    list_documents,
    open_document_download,
    upload_document,
)

from .serializers import (
    DocumentListResponseSerializer,
    DocumentResponseSerializer,
    DocumentUploadSerializer,
)


class DocumentTooLarge(APIException):
    status_code = 413
    default_detail = "The document exceeds the 20 MiB upload limit."
    default_code = "file_too_large"


class UnsupportedDocument(APIException):
    status_code = 415
    default_detail = "The file extension and detected content must be supported."
    default_code = "unsupported_document"


class DocumentMutationConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Documents can only be uploaded to draft or active projects."
    default_code = "conflict"


def _query_int(request, *, name, default):
    raw_value = request.query_params.get(name, default)
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: "Enter a valid integer."}) from exc
    return value


def _page_url(request, page):
    if page is None:
        return None
    query = request.query_params.copy()
    query["page"] = str(page)
    return request.build_absolute_uri(f"{request.path}?{query.urlencode()}")


class ProjectDocumentListCreateView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["documents"],
        operation_id="project_documents_list",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                enum=["active", "archived", "deletion_pending"],
                required=False,
            ),
            OpenApiParameter(name="page", type=OpenApiTypes.INT, required=False),
            OpenApiParameter(name="page_size", type=OpenApiTypes.INT, required=False),
        ],
        responses={
            200: DocumentListResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, project_id):
        try:
            page = list_documents(
                project_id=project_id,
                actor=request.user,
                status=request.query_params.get("status"),
                page=request.query_params.get("page", 1),
                page_size=_query_int(request, name="page_size", default=20),
            )
        except DocumentNotFoundError as exc:
            raise NotFound("Project not found.") from exc

        return Response(
            {
                "count": page.count,
                "next": _page_url(request, page.next_page),
                "previous": _page_url(request, page.previous_page),
                "results": DocumentResponseSerializer(page.results, many=True).data,
            }
        )

    @extend_schema(
        tags=["documents"],
        operation_id="project_documents_upload",
        request=DocumentUploadSerializer,
        responses={
            201: DocumentResponseSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
            409: ErrorEnvelopeSerializer,
            413: ErrorEnvelopeSerializer,
            415: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request, project_id):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            document = upload_document(
                project_id=project_id,
                actor=request.user,
                file=serializer.validated_data["file"],
            )
        except DocumentNotFoundError as exc:
            raise NotFound("Project not found.") from exc
        except DocumentStateConflictError as exc:
            raise DocumentMutationConflict() from exc
        except DocumentTooLargeError as exc:
            raise DocumentTooLarge() from exc
        except UnsupportedDocumentError as exc:
            raise UnsupportedDocument() from exc

        return Response(
            DocumentResponseSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["documents"],
        operation_id="documents_retrieve",
        responses={
            200: DocumentResponseSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, document_id):
        try:
            document = get_document(document_id=document_id, actor=request.user)
        except DocumentNotFoundError as exc:
            raise NotFound("Document not found.") from exc
        return Response(DocumentResponseSerializer(document).data)


class DocumentDownloadView(CsrfSanitizingAPIView):
    permission_classes = [RequireAuthenticatedUser, RequireCsrfForUnsafeRequests]

    @extend_schema(
        tags=["documents"],
        operation_id="documents_download",
        responses={
            (200, "application/pdf"): OpenApiTypes.BINARY,
            (
                200,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ): OpenApiTypes.BINARY,
            (200, "text/plain"): OpenApiTypes.BINARY,
            (200, "text/markdown"): OpenApiTypes.BINARY,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request, document_id):
        try:
            document, file_handle = open_document_download(
                document_id=document_id,
                actor=request.user,
            )
        except DocumentNotFoundError as exc:
            raise NotFound("Document not found.") from exc

        response = FileResponse(
            file_handle,
            as_attachment=True,
            filename=document.original_filename,
            content_type=document.mime_type,
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
