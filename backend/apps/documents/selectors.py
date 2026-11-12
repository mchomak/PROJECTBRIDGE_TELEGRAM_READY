from django.db.models import Prefetch

from apps.projects.models import ProjectMemberStatus

from .models import Document, DocumentLifecycleRequest, DocumentLifecycleStatus


def _with_lifecycle_requests(documents):
    return documents.prefetch_related(
        Prefetch(
            "lifecycle_requests",
            queryset=DocumentLifecycleRequest.objects.prefetch_related("approvals"),
        )
    )


def get_documents_for_member(*, project_id, actor, status=None):
    documents = _with_lifecycle_requests(
        Document.objects.filter(
            project_id=project_id,
            project__memberships__user=actor,
            project__memberships__status=ProjectMemberStatus.ACTIVE,
        )
    ).exclude(lifecycle_status=DocumentLifecycleStatus.DELETED)

    if status == "archived":
        return documents.filter(lifecycle_status=DocumentLifecycleStatus.ARCHIVED)
    if status == "deletion_pending":
        return documents.filter(
            lifecycle_status=DocumentLifecycleStatus.DELETION_PENDING
        )
    return documents.filter(
        lifecycle_status__in=(
            DocumentLifecycleStatus.ACTIVE,
            DocumentLifecycleStatus.ARCHIVE_PENDING,
        )
    )


def get_document_for_member(*, document_id, actor):
    return (
        Document.objects.filter(
            pk=document_id,
            project__memberships__user=actor,
            project__memberships__status=ProjectMemberStatus.ACTIVE,
        )
        .exclude(lifecycle_status=DocumentLifecycleStatus.DELETED)
        .select_related("project")
        .prefetch_related("lifecycle_requests__approvals")
        .first()
    )
