from apps.projects.models import ProjectMemberStatus

from .models import Message


def get_messages_for_member(*, project_id, actor):
    return (
        Message.objects.filter(
            project_id=project_id,
            project__memberships__user=actor,
            project__memberships__status=ProjectMemberStatus.ACTIVE,
        )
        .select_related("sender")
        .distinct()
    )


def get_message_for_evidence(*, project_id, message_id):
    """Resolve a message source while enforcing its project boundary."""
    return Message.objects.filter(project_id=project_id, pk=message_id).first()
