from apps.projects.models import ProjectMemberStatus

from .models import Document, DocumentLifecycleStatus


def get_documents_for_member(*, project_id, actor, status=None):
    documents = Document.objects.filter(
        project_id=project_id,
        project__memberships__user=actor,
        project__memberships__status=ProjectMemberStatus.ACTIVE,
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
        .first()
    )
