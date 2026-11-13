import hashlib
import logging
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.utils import timezone

from apps.common.services import record_project_action
from apps.documents.docx_safety import DocxArchiveError, docx_archive_names
from apps.projects.models import (
    Project,
    ProjectMember,
    ProjectMemberStatus,
    ProjectStatus,
)

from .models import (
    Document,
    DocumentLifecycleAction,
    DocumentLifecycleApproval,
    DocumentLifecycleDecision,
    DocumentLifecycleRequest,
    DocumentLifecycleRequestStatus,
    DocumentLifecycleStatus,
    DocumentProcessingStatus,
)
from .selectors import get_document_for_member, get_documents_for_member

MAX_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024
DEFAULT_DOCUMENT_PAGE_SIZE = 20
MAX_DOCUMENT_PAGE_SIZE = 100
logger = logging.getLogger(__name__)

_EXTENSION_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}


class DocumentNotFoundError(Exception):
    """The document or project is not visible to the active member."""


class DocumentStateConflictError(Exception):
    """The project state does not allow document mutations."""


class DocumentLifecyclePermissionError(Exception):
    """The active project member cannot decide this lifecycle request."""


class DocumentTooLargeError(Exception):
    """The document exceeds the server upload limit."""


class UnsupportedDocumentError(Exception):
    """The extension and detected file content are unsupported or mismatched."""


@dataclass(frozen=True)
class DocumentListPage:
    count: int
    results: list[Document]
    next_page: int | None
    previous_page: int | None


def _display_filename(filename):
    normalized = str(filename or "").replace("\\", "/")
    basename = PurePosixPath(normalized).name.strip()
    if basename in {"", ".", ".."}:
        basename = "document"
    basename = "".join(
        character for character in basename if unicodedata.category(character) != "Cc"
    )
    if len(basename) <= 255:
        return basename
    suffix = PurePosixPath(basename).suffix
    if len(suffix) >= 255:
        return basename[:255]
    return f"{basename[: 255 - len(suffix)]}{suffix}"


def _text_content_is_valid(contents):
    try:
        if contents.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
            decoded = contents.decode("utf-32")
        elif contents.startswith((b"\xff\xfe", b"\xfe\xff")):
            decoded = contents.decode("utf-16")
        else:
            decoded = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False

    return all(
        unicodedata.category(character) != "Cc" or character in "\t\n\r\f"
        for character in decoded
    )


def _detected_mime_type(contents):
    if b"%PDF-" in contents[:1024]:
        return "application/pdf"

    try:
        names = docx_archive_names(contents)
    except (DocxArchiveError, OSError):
        names = set()

    if "[Content_Types].xml" in names and "word/document.xml" in names:
        return _EXTENSION_MIME_TYPES[".docx"]
    if names:
        return "application/zip"
    if _text_content_is_valid(contents):
        return "text/plain"
    return "application/octet-stream"


def _validate_document(*, filename, contents):
    extension = PurePosixPath(filename).suffix.lower()
    expected_mime_type = _EXTENSION_MIME_TYPES.get(extension)
    detected_mime_type = _detected_mime_type(contents)
    if expected_mime_type is None:
        raise UnsupportedDocumentError

    if extension in {".txt", ".md", ".markdown"}:
        if detected_mime_type != "text/plain":
            raise UnsupportedDocumentError
    elif detected_mime_type != expected_mime_type:
        raise UnsupportedDocumentError

    return expected_mime_type


def _get_active_member_project(*, project_id, actor, lock=False):
    projects = Project.objects
    memberships = ProjectMember.objects
    if lock:
        projects = projects.select_for_update()
        memberships = memberships.select_for_update()

    project = projects.filter(pk=project_id).first()
    if project is None:
        raise DocumentNotFoundError
    member = memberships.filter(
        project_id=project_id,
        user=actor,
        status=ProjectMemberStatus.ACTIVE,
    ).first()
    if member is None:
        raise DocumentNotFoundError
    return project


def upload_document(*, project_id, actor, file):
    file_size = getattr(file, "size", None)
    if isinstance(file_size, bool) or not isinstance(file_size, int):
        raise ValidationError({"file": "A valid uploaded file is required."})
    if file_size > MAX_DOCUMENT_SIZE_BYTES:
        raise DocumentTooLargeError

    try:
        file.seek(0)
        contents = file.read()
    except (AttributeError, OSError) as exc:
        raise ValidationError({"file": "The uploaded file could not be read."}) from exc

    if len(contents) > MAX_DOCUMENT_SIZE_BYTES:
        raise DocumentTooLargeError
    if len(contents) != file_size:
        raise ValidationError({"file": "The uploaded file could not be read."})

    filename = _display_filename(getattr(file, "name", None))
    mime_type = _validate_document(filename=filename, contents=contents)
    storage_key = None

    try:
        with transaction.atomic():
            project = _get_active_member_project(
                project_id=project_id,
                actor=actor,
                lock=True,
            )
            if project.status not in (ProjectStatus.DRAFT, ProjectStatus.ACTIVE):
                raise DocumentStateConflictError

            storage_key = default_storage.save(
                f"documents/{project.pk}/{uuid.uuid4()}",
                ContentFile(contents),
            )
            document = Document.objects.create(
                project=project,
                uploaded_by=actor,
                original_filename=filename,
                mime_type=mime_type,
                file_size=len(contents),
                checksum_sha256=hashlib.sha256(contents).hexdigest(),
                storage_key=storage_key,
                lifecycle_status=DocumentLifecycleStatus.ACTIVE,
            )
            from apps.documents.tasks import process_project_document

            transaction.on_commit(
                lambda document_id=str(document.pk): process_project_document.delay(
                    document_id
                )
            )
            return document
    except Exception:
        if storage_key is not None:
            try:
                default_storage.delete(storage_key)
            except Exception:
                logger.exception("Failed to clean up a partial document upload.")
        raise


def list_documents(*, project_id, actor, status=None, page=1, page_size=20):
    _get_active_member_project(project_id=project_id, actor=actor)
    if status not in (None, "active", "archived", "deletion_pending"):
        raise ValidationError({"status": "Select a valid choice."})
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
        raise ValidationError({"page_size": "Page size must be between 1 and 100."})
    page_size = min(page_size, MAX_DOCUMENT_PAGE_SIZE)

    documents = get_documents_for_member(
        project_id=project_id,
        actor=actor,
        status=status,
    )
    paginator = Paginator(documents, page_size)
    try:
        result_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger) as exc:
        raise ValidationError({"page": "Enter a valid page number."}) from exc

    return DocumentListPage(
        count=paginator.count,
        results=list(result_page.object_list),
        next_page=(result_page.next_page_number() if result_page.has_next() else None),
        previous_page=(
            result_page.previous_page_number() if result_page.has_previous() else None
        ),
    )


def get_document(*, document_id, actor):
    document = get_document_for_member(document_id=document_id, actor=actor)
    if document is None:
        raise DocumentNotFoundError
    return document


def open_document_download(*, document_id, actor):
    document = get_document(document_id=document_id, actor=actor)
    try:
        return document, default_storage.open(document.storage_key, "rb")
    except (FileNotFoundError, OSError) as exc:
        raise DocumentNotFoundError from exc


def queue_document_embedding_reindex(*, project_id=None):
    """Queue a maintenance reindex for active and archived source documents."""
    documents = Document.objects.filter(
        lifecycle_status__in=(
            DocumentLifecycleStatus.ACTIVE,
            DocumentLifecycleStatus.ARCHIVED,
        )
    ).exclude(processing_status=DocumentProcessingStatus.UNSUPPORTED)
    if project_id is not None:
        documents = documents.filter(project_id=project_id)
    document_ids = list(documents.order_by("pk").values_list("pk", flat=True))
    if not document_ids:
        return 0

    from apps.documents.tasks import reindex_project_document

    transaction.on_commit(
        lambda ids=tuple(str(document_id) for document_id in document_ids): [
            reindex_project_document.delay(document_id) for document_id in ids
        ]
    )
    return len(document_ids)


def _lock_member_document(*, document_id, actor):
    candidate = get_document_for_member(document_id=document_id, actor=actor)
    if candidate is None:
        raise DocumentNotFoundError

    project = _get_active_member_project(
        project_id=candidate.project_id,
        actor=actor,
        lock=True,
    )
    document = (
        Document.objects.select_for_update()
        .filter(pk=document_id, project_id=project.pk)
        .exclude(lifecycle_status=DocumentLifecycleStatus.DELETED)
        .first()
    )
    if document is None:
        raise DocumentNotFoundError
    return project, document


def _lock_member_lifecycle_request(*, request_id, actor):
    candidate = (
        DocumentLifecycleRequest.objects.filter(
            pk=request_id,
            document__project__memberships__user=actor,
            document__project__memberships__status=ProjectMemberStatus.ACTIVE,
        )
        .exclude(document__lifecycle_status=DocumentLifecycleStatus.DELETED)
        .select_related("document")
        .first()
    )
    if candidate is None:
        raise DocumentNotFoundError

    project = _get_active_member_project(
        project_id=candidate.document.project_id,
        actor=actor,
        lock=True,
    )
    document = (
        Document.objects.select_for_update()
        .filter(pk=candidate.document_id, project_id=project.pk)
        .exclude(lifecycle_status=DocumentLifecycleStatus.DELETED)
        .first()
    )
    if document is None:
        raise DocumentNotFoundError
    lifecycle_request = (
        DocumentLifecycleRequest.objects.select_for_update()
        .filter(pk=request_id, document=document)
        .first()
    )
    if lifecycle_request is None:
        raise DocumentNotFoundError
    return project, document, lifecycle_request


def _require_mutable_project(project):
    if project.status not in (ProjectStatus.DRAFT, ProjectStatus.ACTIVE):
        raise DocumentStateConflictError


def _require_both_active_participants(project_id):
    members = list(
        ProjectMember.objects.select_for_update()
        .filter(project_id=project_id, status=ProjectMemberStatus.ACTIVE)
        .order_by("role")
    )
    if {member.role for member in members} != {"executor", "customer"}:
        raise DocumentStateConflictError
    return members


def _audit_lifecycle_action(*, project_id, actor, action, document):
    record_project_action(
        project_id=project_id,
        actor_id=actor.pk if actor is not None else None,
        action=action,
        target_type="document",
        target_id=document.pk,
        metadata={},
    )


def _enqueue_document_if_queued(document):
    if (
        document.lifecycle_status
        not in (DocumentLifecycleStatus.ACTIVE, DocumentLifecycleStatus.ARCHIVED)
        or document.processing_status != DocumentProcessingStatus.QUEUED
    ):
        return
    from apps.documents.tasks import process_project_document

    transaction.on_commit(
        lambda document_id=str(document.pk): process_project_document.delay(document_id)
    )


def request_lifecycle_action(*, document_id, actor, action):
    if action not in DocumentLifecycleAction.values:
        raise ValidationError({"action": "Select a valid choice."})

    with transaction.atomic():
        project, document = _lock_member_document(document_id=document_id, actor=actor)
        _require_mutable_project(project)
        _require_both_active_participants(project.pk)

        if action == DocumentLifecycleAction.ARCHIVE:
            if document.lifecycle_status != DocumentLifecycleStatus.ACTIVE:
                raise DocumentStateConflictError
        elif document.lifecycle_status != DocumentLifecycleStatus.ARCHIVED:
            raise DocumentStateConflictError

        if DocumentLifecycleRequest.objects.filter(
            document=document,
            action=action,
            status=DocumentLifecycleRequestStatus.PENDING,
        ).exists():
            raise DocumentStateConflictError

        lifecycle_request = DocumentLifecycleRequest.objects.create(
            document=document,
            action=action,
            initiated_by=actor,
        )
        DocumentLifecycleApproval.objects.create(
            request=lifecycle_request,
            user=actor,
            decision=DocumentLifecycleDecision.APPROVED,
        )

        if action == DocumentLifecycleAction.ARCHIVE:
            document.lifecycle_status = DocumentLifecycleStatus.ARCHIVE_PENDING
            document.save(update_fields=["lifecycle_status"])
            audit_action = "document.archive_requested"
        else:
            audit_action = "document.permanent_delete_requested"

        _audit_lifecycle_action(
            project_id=project.pk,
            actor=actor,
            action=audit_action,
            document=document,
        )
        return lifecycle_request


def decide_lifecycle_request(*, request_id, actor, decision):
    if decision not in DocumentLifecycleDecision.values:
        raise ValidationError({"decision": "Select a valid choice."})

    with transaction.atomic():
        project, document, lifecycle_request = _lock_member_lifecycle_request(
            request_id=request_id,
            actor=actor,
        )
        _require_mutable_project(project)
        members = _require_both_active_participants(project.pk)
        if lifecycle_request.initiated_by_id == actor.pk or actor.pk not in {
            member.user_id for member in members
        }:
            raise DocumentLifecyclePermissionError

        existing_approval = lifecycle_request.approvals.filter(user=actor).first()
        if existing_approval is not None:
            if existing_approval.decision == decision and lifecycle_request.status == (
                DocumentLifecycleRequestStatus.REJECTED
                if decision == DocumentLifecycleDecision.REJECTED
                else DocumentLifecycleRequestStatus.APPROVED
            ):
                return lifecycle_request
            raise DocumentStateConflictError

        if lifecycle_request.status != DocumentLifecycleRequestStatus.PENDING:
            raise DocumentStateConflictError
        if lifecycle_request.action == DocumentLifecycleAction.ARCHIVE:
            expected_status = DocumentLifecycleStatus.ARCHIVE_PENDING
        else:
            expected_status = DocumentLifecycleStatus.ARCHIVED
        if document.lifecycle_status != expected_status:
            raise DocumentStateConflictError

        DocumentLifecycleApproval.objects.create(
            request=lifecycle_request,
            user=actor,
            decision=decision,
        )

        if decision == DocumentLifecycleDecision.REJECTED:
            lifecycle_request.status = DocumentLifecycleRequestStatus.REJECTED
            if lifecycle_request.action == DocumentLifecycleAction.ARCHIVE:
                document.lifecycle_status = DocumentLifecycleStatus.ACTIVE
                document.save(update_fields=["lifecycle_status"])
            audit_action = f"document.{lifecycle_request.action}_rejected"
        else:
            lifecycle_request.status = DocumentLifecycleRequestStatus.APPROVED
            audit_action = f"document.{lifecycle_request.action}_approved"
            if lifecycle_request.action == DocumentLifecycleAction.ARCHIVE:
                document.lifecycle_status = DocumentLifecycleStatus.ARCHIVED
                document.archived_at = timezone.now()
                document.save(update_fields=["lifecycle_status", "archived_at"])
            else:
                now = timezone.now()
                document.lifecycle_status = DocumentLifecycleStatus.DELETION_PENDING
                lifecycle_request.deletion_after = now + timedelta(days=30)
                document.save(update_fields=["lifecycle_status"])

        lifecycle_request.save(
            update_fields=["status", "deletion_after"],
        )
        _enqueue_document_if_queued(document)
        _audit_lifecycle_action(
            project_id=project.pk,
            actor=actor,
            action=audit_action,
            document=document,
        )
        return lifecycle_request


def restore_document(*, document_id, actor):
    with transaction.atomic():
        project, document = _lock_member_document(document_id=document_id, actor=actor)
        _require_mutable_project(project)
        if document.lifecycle_status != DocumentLifecycleStatus.ARCHIVED:
            raise DocumentStateConflictError

        pending_deletion = (
            DocumentLifecycleRequest.objects.select_for_update()
            .filter(
                document=document,
                action=DocumentLifecycleAction.PERMANENT_DELETE,
                status=DocumentLifecycleRequestStatus.PENDING,
            )
            .first()
        )
        if pending_deletion is not None:
            pending_deletion.status = DocumentLifecycleRequestStatus.CANCELLED
            pending_deletion.save(update_fields=["status"])
            _audit_lifecycle_action(
                project_id=project.pk,
                actor=actor,
                action="document.permanent_delete_request_cancelled_by_restore",
                document=document,
            )

        document.lifecycle_status = DocumentLifecycleStatus.ACTIVE
        document.archived_at = None
        document.save(update_fields=["lifecycle_status", "archived_at"])
        _enqueue_document_if_queued(document)
        _audit_lifecycle_action(
            project_id=project.pk,
            actor=actor,
            action="document.restored",
            document=document,
        )
        return document


def cancel_lifecycle_request(*, request_id, actor):
    with transaction.atomic():
        _project, document, lifecycle_request = _lock_member_lifecycle_request(
            request_id=request_id,
            actor=actor,
        )
        now = timezone.now()
        if (
            lifecycle_request.action != DocumentLifecycleAction.PERMANENT_DELETE
            or lifecycle_request.status != DocumentLifecycleRequestStatus.APPROVED
            or document.lifecycle_status != DocumentLifecycleStatus.DELETION_PENDING
            or lifecycle_request.deletion_after is None
            or now >= lifecycle_request.deletion_after
        ):
            raise DocumentStateConflictError

        lifecycle_request.status = DocumentLifecycleRequestStatus.CANCELLED
        lifecycle_request.save(update_fields=["status"])
        document.lifecycle_status = DocumentLifecycleStatus.ARCHIVED
        document.save(update_fields=["lifecycle_status"])
        _enqueue_document_if_queued(document)
        _audit_lifecycle_action(
            project_id=document.project_id,
            actor=actor,
            action="document.permanent_delete_cancelled",
            document=document,
        )
        return lifecycle_request


def process_expired_deletions():
    candidate_rows = list(
        DocumentLifecycleRequest.objects.filter(
            action=DocumentLifecycleAction.PERMANENT_DELETE,
            status=DocumentLifecycleRequestStatus.APPROVED,
            deletion_after__lte=timezone.now(),
            document__lifecycle_status=DocumentLifecycleStatus.DELETION_PENDING,
        )
        .order_by("deletion_after", "id")
        .values_list("document__project_id", "document_id", "id")
    )
    completed = 0

    for project_id, document_id, request_id in candidate_rows:
        with transaction.atomic():
            project = Project.objects.select_for_update().filter(pk=project_id).first()
            document = (
                Document.objects.select_for_update()
                .filter(pk=document_id, project_id=project_id)
                .first()
            )
            lifecycle_request = (
                DocumentLifecycleRequest.objects.select_for_update()
                .filter(pk=request_id, document_id=document_id)
                .first()
            )
            if project is None or document is None or lifecycle_request is None:
                continue
            if (
                lifecycle_request.action != DocumentLifecycleAction.PERMANENT_DELETE
                or lifecycle_request.status != DocumentLifecycleRequestStatus.APPROVED
                or lifecycle_request.deletion_after is None
                or timezone.now() < lifecycle_request.deletion_after
                or document.lifecycle_status != DocumentLifecycleStatus.DELETION_PENDING
            ):
                continue

            default_storage.delete(document.storage_key)
            document.chunks.all().delete()
            document.original_filename = ""
            document.mime_type = ""
            document.file_size = 0
            document.checksum_sha256 = hashlib.sha256(b"").hexdigest()
            document.lifecycle_status = DocumentLifecycleStatus.DELETED
            document.deleted_at = timezone.now()
            document.save(
                update_fields=[
                    "original_filename",
                    "mime_type",
                    "file_size",
                    "checksum_sha256",
                    "lifecycle_status",
                    "deleted_at",
                ]
            )
            lifecycle_request.status = DocumentLifecycleRequestStatus.COMPLETED
            lifecycle_request.completed_at = document.deleted_at
            lifecycle_request.save(update_fields=["status", "completed_at"])
            _audit_lifecycle_action(
                project_id=project.pk,
                actor=None,
                action="document.deleted_by_mutual_consent",
                document=document,
            )
            completed += 1

    return completed
