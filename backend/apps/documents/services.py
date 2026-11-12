import hashlib
import io
import logging
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction

from apps.projects.models import (
    Project,
    ProjectMember,
    ProjectMemberStatus,
    ProjectStatus,
)

from .models import Document, DocumentLifecycleStatus
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
        with zipfile.ZipFile(io.BytesIO(contents)) as archive:
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile):
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
            return Document.objects.create(
                project=project,
                uploaded_by=actor,
                original_filename=filename,
                mime_type=mime_type,
                file_size=len(contents),
                checksum_sha256=hashlib.sha256(contents).hexdigest(),
                storage_key=storage_key,
                lifecycle_status=DocumentLifecycleStatus.ACTIVE,
            )
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
