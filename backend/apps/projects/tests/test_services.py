import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_create_project_starts_with_executor_membership_empty_passport_and_audit():
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import Project, ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    actor = get_user_model().objects.create_user(email="executor@example.com")

    project = create_project(
        actor=actor,
        data={
            "name": "Website refresh",
            "project_type": "website",
            "description": None,
        },
    )

    member = ProjectMember.objects.get(project=project, user=actor)
    passport = ProjectPassport.objects.get(project=project)
    audit = ProjectAuditLog.objects.get(project=project)

    assert project.status == "draft"
    assert project.created_by_id == actor.pk
    assert {field.name for field in Project._meta.concrete_fields} == {
        "id",
        "name",
        "description",
        "project_type",
        "status",
        "status_before_archive",
        "created_by",
        "created_at",
        "updated_at",
        "completed_at",
        "archived_at",
    }
    assert (member.role, member.status) == ("executor", "active")
    assert {field.name for field in ProjectMember._meta.concrete_fields} == {
        "id",
        "project",
        "user",
        "role",
        "status",
        "joined_at",
    }
    assert {field.name for field in ProjectPassport._meta.concrete_fields} == {
        "id",
        "project",
        "goal",
        "target_audience",
        "expected_result",
        "functional_scope",
        "integrations",
        "constraints",
        "deadline",
        "budget_min",
        "budget_max",
        "currency",
        "additional_data",
        "version",
        "created_at",
        "updated_at",
    }
    assert passport.version == 1
    assert passport.goal == passport.target_audience == passport.expected_result == ""
    assert passport.functional_scope == passport.integrations == {}
    assert passport.constraints == passport.additional_data == {}
    assert passport.deadline is None
    assert passport.budget_min is None and passport.budget_max is None
    assert passport.currency is None
    assert ProjectPassport._meta.get_field("currency").max_length == 3
    assert (
        ProjectPassport._meta.get_field("budget_min").get_internal_type()
        == "DecimalField"
    )
    assert (audit.actor_id, audit.action, audit.target_type) == (
        actor.pk,
        "project.created",
        "project",
    )
    assert audit.target_id == str(project.pk)
    assert audit.metadata == {}
    assert "Website refresh" not in str(audit.metadata)


@pytest.mark.django_db
def test_create_project_rolls_back_all_rows_when_passport_creation_fails(monkeypatch):
    from apps.projects.models import Project, ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    actor = get_user_model().objects.create_user(email="rollback@example.com")

    def fail_passport_save(self, *args, **kwargs):
        raise RuntimeError("simulated passport persistence failure")

    monkeypatch.setattr(ProjectPassport, "save", fail_passport_save)

    with pytest.raises(RuntimeError, match="simulated passport persistence failure"):
        create_project(
            actor=actor,
            data={"name": "Rollback", "project_type": "website"},
        )

    assert Project.objects.filter(created_by=actor).count() == 0
    assert ProjectMember.objects.filter(user=actor).count() == 0
    assert ProjectPassport.objects.count() == 0


@pytest.mark.django_db
def test_database_constraints_reject_invalid_project_and_membership_state():
    from django.db import IntegrityError, transaction
    from django.utils import timezone

    from apps.projects.models import Project, ProjectMember
    from apps.projects.services import create_project

    actor = get_user_model().objects.create_user(email="constraints@example.com")
    second_user = get_user_model().objects.create_user(email="second@example.com")
    third_user = get_user_model().objects.create_user(email="third@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Constraint checks", "project_type": "website"},
    )

    def assert_database_rejects(operation):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                operation()

    assert_database_rejects(
        lambda: ProjectMember.objects.create(
            project=project,
            user=actor,
            role="customer",
            status="active",
        )
    )
    assert_database_rejects(
        lambda: ProjectMember.objects.create(
            project=project,
            user=second_user,
            role="executor",
            status="active",
        )
    )
    assert_database_rejects(
        lambda: ProjectMember.objects.create(
            project=project,
            user=second_user,
            role="observer",
            status="active",
        )
    )
    assert_database_rejects(
        lambda: ProjectMember.objects.create(
            project=project,
            user=third_user,
            role="customer",
            status="pending",
        )
    )
    assert_database_rejects(
        lambda: Project.objects.filter(pk=project.pk).update(project_type="unknown")
    )
    assert_database_rejects(
        lambda: Project.objects.filter(pk=project.pk).update(status="unknown")
    )
    assert_database_rejects(
        lambda: Project.objects.filter(pk=project.pk).update(status="archived")
    )
    assert_database_rejects(
        lambda: Project.objects.filter(pk=project.pk).update(
            status_before_archive="draft"
        )
    )
    assert_database_rejects(
        lambda: Project.objects.filter(pk=project.pk).update(archived_at=timezone.now())
    )
