import hashlib
import io
import re
import zipfile
from datetime import datetime, timedelta

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


def _create_active_document_pair(*, suffix):
    from apps.documents.models import Document
    from apps.projects.models import ProjectMember, ProjectMemberRole, ProjectStatus
    from apps.projects.services import create_project

    executor = _verified_user(f"{suffix}-executor@example.com")
    customer = _verified_user(f"{suffix}-customer@example.com")
    project = create_project(
        actor=executor,
        data={"name": f"{suffix} documents", "project_type": "website"},
    )
    project.status = ProjectStatus.ACTIVE
    project.save(update_fields=["status"])
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
    )
    executor_client, executor_csrf = _authenticated_client(executor)
    customer_client, customer_csrf = _authenticated_client(customer)
    upload = _upload(
        executor_client,
        executor_csrf,
        project,
        "shared.txt",
        b"shared lifecycle content",
    )
    document = Document.objects.get(pk=upload.data["id"])
    return {
        "executor": executor,
        "customer": customer,
        "project": project,
        "document": document,
        "executor_client": executor_client,
        "executor_csrf": executor_csrf,
        "customer_client": customer_client,
        "customer_csrf": customer_csrf,
    }


def _archive_document_via_api(resource):
    document = resource["document"]
    executor_client = resource["executor_client"]
    executor_csrf = resource["executor_csrf"]
    customer_client = resource["customer_client"]
    customer_csrf = resource["customer_csrf"]
    requested = executor_client.post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "archive"},
        format="json",
        **executor_csrf,
    )
    assert requested.status_code == 201
    approved = customer_client.post(
        f"/api/v1/document-lifecycle-requests/{requested.data['id']}/approve/",
        {},
        format="json",
        **customer_csrf,
    )
    assert approved.status_code == 200
    return requested


def _request_deletion_via_api(resource):
    document = resource["document"]
    executor_client = resource["executor_client"]
    executor_csrf = resource["executor_csrf"]
    customer_client = resource["customer_client"]
    customer_csrf = resource["customer_csrf"]
    requested = customer_client.post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "permanent_delete"},
        format="json",
        **customer_csrf,
    )
    assert requested.status_code == 201
    approved = executor_client.post(
        f"/api/v1/document-lifecycle-requests/{requested.data['id']}/approve/",
        {},
        format="json",
        **executor_csrf,
    )
    assert approved.status_code == 200
    return approved


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
        "lifecycle_request",
    }
    assert response.data["project_id"] == str(project.pk)
    assert response.data["uploaded_by_id"] == str(actor.pk)
    assert response.data["original_filename"] == "scope.md"
    assert response.data["mime_type"] == "text/markdown"
    assert response.data["file_size"] == len(contents)
    assert response.data["checksum_sha256"] == hashlib.sha256(contents).hexdigest()
    assert response.data["lifecycle_status"] == "active"
    assert response.data["processing_status"] == "queued"
    assert response.data["lifecycle_request"] is None
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


@pytest.mark.django_db
def test_archive_request_rejection_returns_document_to_active_state(
    temporary_media_root,
):
    from apps.documents.models import (
        Document,
        DocumentLifecycleApproval,
        DocumentLifecycleRequest,
    )
    from apps.projects.models import ProjectMember, ProjectMemberRole, ProjectStatus
    from apps.projects.services import create_project

    executor = _verified_user("document-archive-executor@example.com")
    customer = _verified_user("document-archive-customer@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Archive consent", "project_type": "website"},
    )
    project.status = ProjectStatus.ACTIVE
    project.save(update_fields=["status"])
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
    )
    executor_client, executor_csrf = _authenticated_client(executor)
    customer_client, customer_csrf = _authenticated_client(customer)
    upload = _upload(executor_client, executor_csrf, project, "shared.txt", b"shared")
    document = Document.objects.get(pk=upload.data["id"])

    requested = executor_client.post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "archive"},
        format="json",
        **executor_csrf,
    )
    request = DocumentLifecycleRequest.objects.get(document=document)

    assert requested.status_code == 201
    assert request.status == "pending"
    assert request.approvals.count() == 1
    assert request.approvals.get().user_id == executor.pk
    document.refresh_from_db()
    assert document.lifecycle_status == "archive_pending"

    rejected = customer_client.post(
        f"/api/v1/document-lifecycle-requests/{request.pk}/reject/",
        {},
        format="json",
        **customer_csrf,
    )

    assert rejected.status_code == 200
    assert rejected.data["status"] == "rejected"
    assert DocumentLifecycleApproval.objects.filter(
        request=request,
        user=customer,
        decision="rejected",
    ).exists()
    document.refresh_from_db()
    assert document.lifecycle_status == "active"
    active_list = customer_client.get(f"/api/v1/projects/{project.pk}/documents/")
    assert [item["id"] for item in active_list.data["results"]] == [str(document.pk)]


@pytest.mark.django_db
def test_both_members_archive_then_restore_as_separate_lifecycle_actions(
    temporary_media_root,
):
    from apps.common.models import ProjectAuditLog
    from apps.documents.models import Document
    from apps.projects.models import ProjectMember, ProjectMemberRole, ProjectStatus
    from apps.projects.services import create_project

    executor = _verified_user("document-mutual-archive-executor@example.com")
    customer = _verified_user("document-mutual-archive-customer@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Mutual archive", "project_type": "website"},
    )
    project.status = ProjectStatus.ACTIVE
    project.save(update_fields=["status"])
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
    )
    executor_client, executor_csrf = _authenticated_client(executor)
    customer_client, customer_csrf = _authenticated_client(customer)
    upload = _upload(executor_client, executor_csrf, project, "shared.txt", b"shared")
    document = Document.objects.get(pk=upload.data["id"])
    requested = executor_client.post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "archive"},
        format="json",
        **executor_csrf,
    )

    approved = customer_client.post(
        f"/api/v1/document-lifecycle-requests/{requested.data['id']}/approve/",
        {},
        format="json",
        **customer_csrf,
    )
    document.refresh_from_db()
    assert approved.status_code == 200
    assert approved.data["status"] == "approved"
    assert approved.data["viewer_decision"] == "approved"
    assert document.lifecycle_status == "archived"
    assert document.archived_at is not None
    assert (
        customer_client.get(f"/api/v1/projects/{project.pk}/documents/").data["results"]
        == []
    )
    archived = customer_client.get(
        f"/api/v1/projects/{project.pk}/documents/?status=archived"
    )
    assert [item["id"] for item in archived.data["results"]] == [str(document.pk)]

    restored = customer_client.post(
        f"/api/v1/documents/{document.pk}/restore/",
        {},
        format="json",
        **customer_csrf,
    )

    assert restored.status_code == 200
    assert restored.data["lifecycle_status"] == "active"
    assert restored.data["archived_at"] is None
    assert restored.data["lifecycle_request"] is None
    assert (
        ProjectAuditLog.objects.filter(
            project=project,
            action__in=[
                "document.archive_requested",
                "document.archive_approved",
                "document.restored",
            ],
        ).count()
        == 3
    )


@pytest.mark.django_db
def test_restoring_archived_document_cancels_pending_deletion_consent(
    temporary_media_root,
):
    from apps.common.models import ProjectAuditLog
    from apps.documents.models import DocumentLifecycleRequest

    resource = _create_active_document_pair(suffix="document-restore-pending-delete")
    document = resource["document"]
    _archive_document_via_api(resource)
    requested = resource["customer_client"].post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "permanent_delete"},
        format="json",
        **resource["customer_csrf"],
    )
    lifecycle_request = DocumentLifecycleRequest.objects.get(pk=requested.data["id"])

    restored = resource["executor_client"].post(
        f"/api/v1/documents/{document.pk}/restore/",
        {},
        format="json",
        **resource["executor_csrf"],
    )

    lifecycle_request.refresh_from_db()
    document.refresh_from_db()
    assert requested.status_code == 201
    assert requested.data["status"] == "pending"
    assert restored.status_code == 200
    assert restored.data["lifecycle_status"] == "active"
    assert restored.data["lifecycle_request"] is None
    assert lifecycle_request.status == "cancelled"
    assert lifecycle_request.approvals.count() == 1
    assert document.lifecycle_status == "active"
    assert (
        ProjectAuditLog.objects.filter(
            project=resource["project"],
            target_id=str(document.pk),
            action__in=[
                "document.restored",
                "document.permanent_delete_request_cancelled_by_restore",
            ],
        ).count()
        == 2
    )

    late_approval = resource["executor_client"].post(
        f"/api/v1/document-lifecycle-requests/{lifecycle_request.pk}/approve/",
        {},
        format="json",
        **resource["executor_csrf"],
    )
    assert late_approval.status_code == 409


@pytest.mark.django_db
def test_permanent_deletion_requires_archived_state_and_starts_grace_at_second_approval(
    monkeypatch,
    temporary_media_root,
):
    from apps.documents import services as document_services
    from apps.documents.models import Document, DocumentLifecycleRequest
    from apps.projects.models import ProjectMember, ProjectMemberRole, ProjectStatus
    from apps.projects.services import create_project

    executor = _verified_user("document-delete-executor@example.com")
    customer = _verified_user("document-delete-customer@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Deletion consent", "project_type": "website"},
    )
    project.status = ProjectStatus.ACTIVE
    project.save(update_fields=["status"])
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
    )
    executor_client, executor_csrf = _authenticated_client(executor)
    customer_client, customer_csrf = _authenticated_client(customer)
    upload = _upload(executor_client, executor_csrf, project, "shared.txt", b"shared")
    document = Document.objects.get(pk=upload.data["id"])

    not_archived = executor_client.post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "permanent_delete"},
        format="json",
        **executor_csrf,
    )
    assert not_archived.status_code == 409
    assert not DocumentLifecycleRequest.objects.filter(
        document=document,
        action="permanent_delete",
    ).exists()

    archive_request = executor_client.post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "archive"},
        format="json",
        **executor_csrf,
    )
    archive_approval = customer_client.post(
        f"/api/v1/document-lifecycle-requests/{archive_request.data['id']}/approve/",
        {},
        format="json",
        **customer_csrf,
    )
    assert archive_approval.status_code == 200
    document.refresh_from_db()
    assert document.lifecycle_status == "archived"

    fixed_now = timezone.now()
    monkeypatch.setattr(document_services.timezone, "now", lambda: fixed_now)
    delete_request_response = customer_client.post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "permanent_delete"},
        format="json",
        **customer_csrf,
    )
    assert delete_request_response.status_code == 201
    assert delete_request_response.data["deletion_after"] is None
    assert len(delete_request_response.data["approvals"]) == 1
    document.refresh_from_db()
    assert document.lifecycle_status == "archived"

    second_approval = executor_client.post(
        f"/api/v1/document-lifecycle-requests/{delete_request_response.data['id']}/approve/",
        {},
        format="json",
        **executor_csrf,
    )
    expected_deadline = fixed_now + timedelta(days=30)

    assert second_approval.status_code == 200
    assert second_approval.data["status"] == "approved"
    assert (
        datetime.fromisoformat(
            second_approval.data["deletion_after"].replace("Z", "+00:00")
        )
        == expected_deadline
    )
    document.refresh_from_db()
    assert document.lifecycle_status == "deletion_pending"


@pytest.mark.django_db
def test_due_sweep_cleans_document_content_and_is_safe_to_retry_after_project_archive(
    monkeypatch,
    temporary_media_root,
):
    from apps.common.models import ProjectAuditLog
    from apps.documents import services as document_services
    from apps.documents.models import (
        Document,
        DocumentChunk,
        DocumentEmbedding,
        DocumentLifecycleRequest,
    )
    from apps.projects.models import ProjectMember, ProjectMemberRole
    from apps.projects.services import archive_project, create_project

    executor = _verified_user("document-sweep-executor@example.com")
    customer = _verified_user("document-sweep-customer@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Scheduled deletion", "project_type": "website"},
    )
    project.status = "active"
    project.save(update_fields=["status"])
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
    )
    executor_client, executor_csrf = _authenticated_client(executor)
    customer_client, customer_csrf = _authenticated_client(customer)
    contents = b"content to remove"
    upload = _upload(executor_client, executor_csrf, project, "source.txt", contents)
    document = Document.objects.get(pk=upload.data["id"])
    storage_key = document.storage_key
    chunk = DocumentChunk.objects.create(
        document=document,
        chunk_index=0,
        content="derived content to remove",
        metadata={"start_char": 0, "end_char": 25},
    )
    DocumentEmbedding.objects.create(
        chunk=chunk,
        embedding_profile_key="document_embedding",
        model_name="text-embedding-3-small",
        embedding=[1.0, *([0.0] * 1535)],
    )

    archive_request = executor_client.post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "archive"},
        format="json",
        **executor_csrf,
    )
    archive_response = customer_client.post(
        f"/api/v1/document-lifecycle-requests/{archive_request.data['id']}/approve/",
        {},
        format="json",
        **customer_csrf,
    )
    assert archive_response.status_code == 200

    fixed_now = timezone.now()
    monkeypatch.setattr(document_services.timezone, "now", lambda: fixed_now)
    delete_request = customer_client.post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "permanent_delete"},
        format="json",
        **customer_csrf,
    )
    approved_delete = executor_client.post(
        f"/api/v1/document-lifecycle-requests/{delete_request.data['id']}/approve/",
        {},
        format="json",
        **executor_csrf,
    )
    assert approved_delete.status_code == 200

    archive_project(project_id=project.pk, actor=executor)
    due_time = fixed_now + timedelta(days=30)
    monkeypatch.setattr(document_services.timezone, "now", lambda: due_time)

    at_deadline_client, at_deadline_csrf = _authenticated_client(customer)
    too_late_to_cancel = at_deadline_client.post(
        f"/api/v1/document-lifecycle-requests/{delete_request.data['id']}/cancel/",
        {},
        format="json",
        **at_deadline_csrf,
    )
    assert too_late_to_cancel.status_code == 409
    assert document_services.process_expired_deletions() == 1
    assert document_services.process_expired_deletions() == 0
    document.refresh_from_db()
    lifecycle_request = DocumentLifecycleRequest.objects.get(
        pk=delete_request.data["id"]
    )

    assert not default_storage.exists(storage_key)
    assert not DocumentChunk.objects.filter(document=document).exists()
    assert not DocumentEmbedding.objects.filter(chunk__document=document).exists()
    assert document.lifecycle_status == "deleted"
    assert document.original_filename == ""
    assert document.mime_type == ""
    assert document.file_size == 0
    assert document.checksum_sha256 == hashlib.sha256(b"").hexdigest()
    assert document.deleted_at == due_time
    assert lifecycle_request.status == "completed"
    assert lifecycle_request.completed_at == due_time
    deletion_audit = ProjectAuditLog.objects.get(
        project=project,
        action="document.deleted_by_mutual_consent",
        target_id=str(document.pk),
    )
    assert deletion_audit.actor_id is None
    assert deletion_audit.metadata == {}
    after_deadline_client, _ = _authenticated_client(customer)
    assert (
        after_deadline_client.get(f"/api/v1/documents/{document.pk}/").status_code
        == 404
    )
    assert (
        after_deadline_client.get(
            f"/api/v1/projects/{project.pk}/documents/?status=deletion_pending"
        ).data["results"]
        == []
    )


@pytest.mark.django_db
def test_active_member_can_cancel_before_deadline_after_project_archive(
    monkeypatch,
    temporary_media_root,
):
    from apps.documents import services as document_services
    from apps.documents.models import DocumentLifecycleRequest
    from apps.projects.services import archive_project

    resource = _create_active_document_pair(suffix="document-cancel")
    document = resource["document"]
    project = resource["project"]
    fixed_now = timezone.now()
    monkeypatch.setattr(document_services.timezone, "now", lambda: fixed_now)
    _archive_document_via_api(resource)
    approved_delete = _request_deletion_via_api(resource)
    deadline = datetime.fromisoformat(
        approved_delete.data["deletion_after"].replace("Z", "+00:00")
    )
    storage_key = document.storage_key
    archive_project(project_id=project.pk, actor=resource["executor"])

    monkeypatch.setattr(
        document_services.timezone,
        "now",
        lambda: deadline - timedelta(microseconds=1),
    )
    cancel_client, cancel_csrf = _authenticated_client(resource["executor"])
    cancelled = cancel_client.post(
        f"/api/v1/document-lifecycle-requests/{approved_delete.data['id']}/cancel/",
        {},
        format="json",
        **cancel_csrf,
    )

    document.refresh_from_db()
    lifecycle_request = DocumentLifecycleRequest.objects.get(
        pk=approved_delete.data["id"]
    )
    assert cancelled.status_code == 200
    assert cancelled.data["status"] == "cancelled"
    assert document.lifecycle_status == "archived"
    assert lifecycle_request.status == "cancelled"

    monkeypatch.setattr(document_services.timezone, "now", lambda: deadline)
    assert document_services.process_expired_deletions() == 0
    assert default_storage.exists(storage_key)


@pytest.mark.django_db
def test_only_other_member_decides_and_cross_project_ids_are_hidden(
    temporary_media_root,
):
    from apps.projects.models import ProjectStatus
    from apps.projects.services import create_project

    resource = _create_active_document_pair(suffix="document-consent-role")
    document = resource["document"]
    requested = resource["executor_client"].post(
        f"/api/v1/documents/{document.pk}/lifecycle-requests/",
        {"action": "archive"},
        format="json",
        **resource["executor_csrf"],
    )
    outsider = _verified_user("document-consent-outsider@example.com")
    other_project = create_project(
        actor=outsider,
        data={"name": "Unrelated project", "project_type": "website"},
    )
    other_project.status = ProjectStatus.ACTIVE
    other_project.save(update_fields=["status"])
    outsider_client, outsider_csrf = _authenticated_client(outsider)

    self_approval = resource["executor_client"].post(
        f"/api/v1/document-lifecycle-requests/{requested.data['id']}/approve/",
        {},
        format="json",
        **resource["executor_csrf"],
    )
    cross_project_decision = outsider_client.post(
        f"/api/v1/document-lifecycle-requests/{requested.data['id']}/approve/",
        {},
        format="json",
        **outsider_csrf,
    )

    assert self_approval.status_code == 403
    assert cross_project_decision.status_code == 404
    assert other_project.pk != resource["project"].pk


@pytest.mark.django_db
def test_restore_requires_archived_document_member_access_and_mutable_project(
    temporary_media_root,
):
    from apps.projects.services import complete_project, create_project, reopen_project

    resource = _create_active_document_pair(suffix="document-restore-eligibility")
    document = resource["document"]
    project = resource["project"]
    active_restore = resource["customer_client"].post(
        f"/api/v1/documents/{document.pk}/restore/",
        {},
        format="json",
        **resource["customer_csrf"],
    )
    archive_request = _archive_document_via_api(resource)
    complete_project(project_id=project.pk, actor=resource["executor"])
    read_only_restore = resource["customer_client"].post(
        f"/api/v1/documents/{document.pk}/restore/",
        {},
        format="json",
        **resource["customer_csrf"],
    )
    outsider = _verified_user("document-restore-outsider@example.com")
    other_project = create_project(
        actor=outsider,
        data={"name": "Other restore project", "project_type": "website"},
    )
    outsider_client, outsider_csrf = _authenticated_client(outsider)
    cross_project_restore = outsider_client.post(
        f"/api/v1/documents/{document.pk}/restore/",
        {},
        format="json",
        **outsider_csrf,
    )

    assert active_restore.status_code == 409
    assert read_only_restore.status_code == 409
    assert cross_project_restore.status_code == 404
    assert archive_request.status_code == 201
    reopen_project(project_id=project.pk, actor=resource["executor"])
    restored = resource["customer_client"].post(
        f"/api/v1/documents/{document.pk}/restore/",
        {},
        format="json",
        **resource["customer_csrf"],
    )
    assert restored.status_code == 200
    assert restored.data["lifecycle_status"] == "active"
    assert other_project.pk != project.pk


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
