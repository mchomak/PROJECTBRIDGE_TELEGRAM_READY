import hashlib
import io
import re
import zipfile

import pytest
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient


def _verified_user(email):
    user = get_user_model().objects.create_user(email=email)
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


def _authenticated_client(user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    csrf_response = client.get("/api/v1/auth/csrf/")
    return client, {"HTTP_X_CSRFTOKEN": csrf_response.data["csrf_token"]}


@pytest.fixture
def temporary_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _docx_contents():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<document />")
    return buffer.getvalue()


def _upload(client, csrf, project, filename, contents, content_type="text/plain"):
    return client.post(
        f"/api/v1/projects/{project.pk}/documents/",
        {
            "file": SimpleUploadedFile(
                filename,
                contents,
                content_type=content_type,
            )
        },
        format="multipart",
        **csrf,
    )


@pytest.mark.django_db
def test_project_member_uploads_shared_text_document_with_server_metadata(
    temporary_media_root,
):
    from apps.projects.services import create_project

    actor = _verified_user("document-upload@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Shared files", "project_type": "website"},
    )
    client, csrf = _authenticated_client(actor)
    contents = b"# Scope\nShared document text.\n"

    response = _upload(
        client,
        csrf,
        project,
        "scope.md",
        contents,
        content_type="application/pdf",
    )

    assert response.status_code == 201
    assert set(response.data) == {
        "id",
        "project_id",
        "uploaded_by_id",
        "original_filename",
        "mime_type",
        "file_size",
        "checksum_sha256",
        "lifecycle_status",
        "processing_status",
        "created_at",
        "archived_at",
        "deleted_at",
    }
    assert response.data["project_id"] == str(project.pk)
    assert response.data["uploaded_by_id"] == str(actor.pk)
    assert response.data["original_filename"] == "scope.md"
    assert response.data["mime_type"] == "text/markdown"
    assert response.data["file_size"] == len(contents)
    assert response.data["checksum_sha256"] == hashlib.sha256(contents).hexdigest()
    assert response.data["lifecycle_status"] == "active"
    assert response.data["processing_status"] == "queued"
    assert "storage_key" not in response.data


@pytest.mark.parametrize(
    ("filename", "contents", "mime_type"),
    [
        ("brief.pdf", b"%PDF-1.7\nbody", "application/pdf"),
        (
            "brief.docx",
            _docx_contents(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("brief.txt", b"Plain UTF-8 text.\n", "text/plain"),
        ("brief.md", b"# Markdown\n", "text/markdown"),
        ("brief.markdown", b"# Markdown\n", "text/markdown"),
    ],
)
@pytest.mark.django_db
def test_upload_accepts_all_supported_document_formats(
    filename,
    contents,
    mime_type,
    temporary_media_root,
):
    from apps.projects.services import create_project

    actor = _verified_user(f"{filename.replace('.', '-')}-formats@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Supported formats", "project_type": "website"},
    )
    client, csrf = _authenticated_client(actor)

    response = _upload(client, csrf, project, filename, contents)

    assert response.status_code == 201
    assert response.data["mime_type"] == mime_type
    assert response.data["processing_status"] == "queued"


@pytest.mark.parametrize(
    ("filename", "contents"),
    [
        ("misnamed.pdf", b"This is plain text, not a PDF."),
        ("misnamed.txt", b"%PDF-1.7\nThis is a PDF."),
        ("misnamed.docx", b"This is plain text, not a DOCX."),
        ("unsupported.py", b"print('no')\n"),
    ],
)
@pytest.mark.django_db
def test_upload_rejects_unsupported_or_mismatched_content(
    filename,
    contents,
    temporary_media_root,
):
    from apps.projects.services import create_project

    actor = _verified_user(f"{filename.replace('.', '-')}-invalid@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Invalid formats", "project_type": "website"},
    )
    client, csrf = _authenticated_client(actor)

    response = _upload(client, csrf, project, filename, contents)

    assert response.status_code == 415
    assert response.data["detail"] == (
        "The file extension and detected content must be supported."
    )


@pytest.mark.django_db
def test_upload_rejects_more_than_twenty_mib_before_saving(temporary_media_root):
    from apps.documents.models import Document
    from apps.projects.services import create_project

    actor = _verified_user("document-size@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Upload size", "project_type": "website"},
    )
    client, csrf = _authenticated_client(actor)

    response = _upload(
        client,
        csrf,
        project,
        "too-large.txt",
        b"x" * (20 * 1024 * 1024 + 1),
    )

    assert response.status_code == 413
    assert response.data["detail"] == "The document exceeds the 20 MiB upload limit."
    assert not Document.objects.filter(project=project).exists()
    assert list(temporary_media_root.iterdir()) == []


@pytest.mark.django_db
def test_upload_accepts_exactly_twenty_mib(temporary_media_root):
    from apps.projects.services import create_project

    actor = _verified_user("document-size-boundary@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Upload size boundary", "project_type": "website"},
    )
    client, csrf = _authenticated_client(actor)

    response = _upload(
        client,
        csrf,
        project,
        "at-limit.txt",
        b"x" * (20 * 1024 * 1024),
    )

    assert response.status_code == 201
    assert response.data["file_size"] == 20 * 1024 * 1024


@pytest.mark.parametrize("filename", ["empty.txt", "empty.md", "empty.markdown"])
@pytest.mark.django_db
def test_upload_accepts_empty_text_file(filename, temporary_media_root):
    from apps.projects.services import create_project

    actor = _verified_user("document-empty-text@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Empty text document", "project_type": "website"},
    )
    client, csrf = _authenticated_client(actor)

    response = _upload(client, csrf, project, filename, b"")

    assert response.status_code == 201
    assert response.data["file_size"] == 0
    assert response.data["checksum_sha256"] == hashlib.sha256(b"").hexdigest()
    assert response.data["processing_status"] == "queued"


@pytest.mark.django_db
def test_upload_uses_generated_key_and_sanitizes_traversal_filename(
    temporary_media_root,
):
    from apps.documents.models import Document
    from apps.projects.services import create_project

    actor = _verified_user("document-traversal@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Filename safety", "project_type": "website"},
    )
    client, csrf = _authenticated_client(actor)

    response = _upload(
        client,
        csrf,
        project,
        "../../../../outside/../notes.md",
        b"# safe display name\n",
    )

    assert response.status_code == 201
    document = Document.objects.get(pk=response.data["id"])
    assert document.original_filename == "notes.md"
    assert re.fullmatch(
        rf"documents/{project.pk}/[0-9a-f-]{{36}}",
        document.storage_key,
    )
    assert "outside" not in document.storage_key
    assert default_storage.exists(document.storage_key)
    assert "storage_key" not in response.data


@pytest.mark.django_db
def test_both_active_project_members_can_list_and_download_shared_documents(
    temporary_media_root,
):
    from apps.documents.models import Document
    from apps.projects.models import ProjectMember, ProjectMemberRole
    from apps.projects.services import create_project

    executor = _verified_user("document-shared-executor@example.com")
    customer = _verified_user("document-shared-customer@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Shared documents", "project_type": "website"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
    )
    executor_client, executor_csrf = _authenticated_client(executor)
    customer_client, customer_csrf = _authenticated_client(customer)
    contents = b"Shared for both participants.\n"
    uploaded = _upload(
        executor_client,
        executor_csrf,
        project,
        "shared.txt",
        contents,
    )
    customer_upload = _upload(
        customer_client,
        customer_csrf,
        project,
        "customer-note.md",
        b"Uploaded by the customer.\n",
    )
    document = Document.objects.get(pk=uploaded.data["id"])

    listed = customer_client.get(f"/api/v1/projects/{project.pk}/documents/")
    detail = customer_client.get(f"/api/v1/documents/{document.pk}/")
    downloaded = customer_client.get(f"/api/v1/documents/{document.pk}/download/")

    assert listed.status_code == 200
    assert customer_upload.status_code == 201
    assert {row["id"] for row in listed.data["results"]} == {
        str(document.pk),
        customer_upload.data["id"],
    }
    assert detail.status_code == 200
    assert detail.data["original_filename"] == "shared.txt"
    assert downloaded.status_code == 200
    assert b"".join(downloaded.streaming_content) == contents
    assert downloaded["X-Content-Type-Options"] == "nosniff"
    assert downloaded["Content-Disposition"].startswith("attachment;")
    assert "public" not in downloaded.get("Cache-Control", "")


@pytest.mark.django_db
def test_document_routes_hide_cross_project_resources_and_require_authentication(
    temporary_media_root,
):
    from apps.projects.services import create_project

    owner = _verified_user("document-owner@example.com")
    outsider = _verified_user("document-outsider@example.com")
    project = create_project(
        actor=owner,
        data={"name": "Private boundary", "project_type": "website"},
    )
    other_project = create_project(
        actor=outsider,
        data={"name": "Other project", "project_type": "website"},
    )
    owner_client, owner_csrf = _authenticated_client(owner)
    outsider_client, _ = _authenticated_client(outsider)
    uploaded = _upload(
        owner_client,
        owner_csrf,
        project,
        "private-boundary.txt",
        b"Not available across projects.",
    )

    assert uploaded.status_code == 201
    assert (
        outsider_client.get(f"/api/v1/projects/{project.pk}/documents/").status_code
        == 404
    )
    assert (
        outsider_client.get(f"/api/v1/documents/{uploaded.data['id']}/").status_code
        == 404
    )
    assert (
        outsider_client.get(
            f"/api/v1/documents/{uploaded.data['id']}/download/"
        ).status_code
        == 404
    )
    assert (
        owner_client.get(f"/api/v1/projects/{other_project.pk}/documents/").status_code
        == 404
    )

    anonymous = APIClient().get(f"/api/v1/documents/{uploaded.data['id']}/download/")
    assert anonymous.status_code == 401


@pytest.mark.django_db
def test_upload_is_blocked_after_project_completion(temporary_media_root):
    from apps.projects.models import ProjectStatus
    from apps.projects.services import create_project

    actor = _verified_user("document-read-only-project@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Read-only documents", "project_type": "website"},
    )
    project.status = ProjectStatus.COMPLETED
    project.save(update_fields=["status"])
    client, csrf = _authenticated_client(actor)

    response = _upload(client, csrf, project, "late.txt", b"No longer active.")

    assert response.status_code == 409
    assert response.data["detail"] == (
        "Documents can only be uploaded to draft or active projects."
    )


@pytest.mark.django_db
def test_storage_bytes_are_removed_when_document_metadata_write_fails(
    monkeypatch,
    temporary_media_root,
):
    from apps.documents import services
    from apps.documents.models import Document
    from apps.projects.services import create_project

    actor = _verified_user("document-cleanup@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Compensating cleanup", "project_type": "website"},
    )
    uploaded_file = SimpleUploadedFile("cleanup.txt", b"cleanup body")
    saved_keys = []
    storage_save = default_storage.save

    def record_save(name, content):
        saved_key = storage_save(name, content)
        saved_keys.append(saved_key)
        return saved_key

    def fail_metadata_write(**kwargs):
        raise RuntimeError("metadata insert failed")

    monkeypatch.setattr(services.default_storage, "save", record_save)
    monkeypatch.setattr(Document.objects, "create", fail_metadata_write)

    with pytest.raises(RuntimeError, match="metadata insert failed"):
        services.upload_document(
            project_id=project.pk,
            actor=actor,
            file=uploaded_file,
        )

    assert len(saved_keys) == 1
    assert not default_storage.exists(saved_keys[0])
    assert Document.objects.filter(project=project).count() == 0


def test_document_download_openapi_describes_binary_content_types():
    from drf_spectacular.generators import SchemaGenerator

    schema = SchemaGenerator().get_schema(request=None, public=True)
    response = schema["paths"]["/api/v1/documents/{document_id}/download/"]["get"][
        "responses"
    ]["200"]
    expected_media_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    }

    assert set(response["content"]) == expected_media_types
    for media_type in expected_media_types:
        assert response["content"][media_type]["schema"] == {
            "type": "string",
            "format": "binary",
        }
