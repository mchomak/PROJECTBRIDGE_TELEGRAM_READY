from .models import (
    Project,
    ProjectMember,
    ProjectMemberStatus,
    ProjectPassport,
    ProjectStatus,
)


def get_projects_for_member(*, user, status=None):
    projects = Project.objects.filter(
        memberships__user=user,
        memberships__status=ProjectMemberStatus.ACTIVE,
    )
    if status == ProjectStatus.ARCHIVED:
        projects = projects.filter(status=ProjectStatus.ARCHIVED)
    else:
        projects = projects.exclude(status=ProjectStatus.ARCHIVED)
    return projects.order_by("-updated_at", "id")


def get_project_for_member(*, project_id, user):
    return Project.objects.filter(
        pk=project_id,
        memberships__user=user,
        memberships__status=ProjectMemberStatus.ACTIVE,
    ).first()


def get_project_invitation_context(*, project_id, user):
    project = get_project_for_member(project_id=project_id, user=user)
    if project is None:
        return None
    membership = (
        ProjectMember.objects.filter(
            project_id=project_id,
            user=user,
            status=ProjectMemberStatus.ACTIVE,
        )
        .only("role")
        .first()
    )
    if membership is None:
        return None
    return project, membership.role


def has_active_customer_membership(*, project_id):
    return ProjectMember.objects.filter(
        project_id=project_id,
        role="customer",
        status=ProjectMemberStatus.ACTIVE,
    ).exists()


def get_active_project_members(*, project_id):
    return (
        ProjectMember.objects.filter(
            project_id=project_id,
            status=ProjectMemberStatus.ACTIVE,
        )
        .select_related("user")
        .order_by("joined_at", "id")
    )


def get_passport_for_member(*, project_id, user):
    return ProjectPassport.objects.filter(
        project_id=project_id,
        project__memberships__user=user,
        project__memberships__status=ProjectMemberStatus.ACTIVE,
    ).first()
