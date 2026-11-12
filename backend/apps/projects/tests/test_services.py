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


@pytest.mark.django_db
def test_project_lifecycle_services_follow_transitions_and_audit_each_mutation():
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import Project, ProjectMember
    from apps.projects.services import (
        archive_project,
        complete_project,
        create_project,
        reopen_project,
        restore_project,
    )

    executor = get_user_model().objects.create_user(email="lifecycle@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Lifecycle", "project_type": "website"},
    )
    membership = ProjectMember.objects.get(project=project, user=executor)

    archived_from_draft = archive_project(project_id=project.pk, actor=executor)
    assert archived_from_draft.status == "archived"
    assert archived_from_draft.status_before_archive == "draft"
    assert archived_from_draft.archived_at is not None
    restored_draft = restore_project(project_id=project.pk, actor=executor)
    assert restored_draft.status == "draft"
    assert restored_draft.status_before_archive is None
    assert restored_draft.archived_at is None

    Project.objects.filter(pk=project.pk).update(status="active")
    completed = complete_project(project_id=project.pk, actor=executor)
    first_completed_at = completed.completed_at
    assert completed.status == "completed"
    assert first_completed_at is not None
    reopened = reopen_project(project_id=project.pk, actor=executor)
    assert reopened.status == "active"
    assert reopened.completed_at == first_completed_at
    archived_from_active = archive_project(project_id=project.pk, actor=executor)
    assert archived_from_active.status_before_archive == "active"
    restored_active = restore_project(project_id=project.pk, actor=executor)
    assert restored_active.status == "active"
    assert restored_active.completed_at == first_completed_at
    completed_again = complete_project(project_id=project.pk, actor=executor)
    assert completed_again.status == "completed"
    assert completed_again.completed_at >= first_completed_at

    archived_from_completed = archive_project(project_id=project.pk, actor=executor)
    assert archived_from_completed.status_before_archive == "completed"
    archived_at = archived_from_completed.archived_at
    restored_completed = restore_project(project_id=project.pk, actor=executor)
    assert restored_completed.status == "completed"
    assert restored_completed.status_before_archive is None
    assert restored_completed.archived_at is None
    assert archived_at is not None

    assert Project.objects.filter(pk=project.pk).exists()
    assert ProjectMember.objects.filter(pk=membership.pk).exists()
    assert ProjectAuditLog.objects.filter(project=project).count() == 10
    lifecycle_audits = (
        ProjectAuditLog.objects.filter(project=project)
        .exclude(action="project.created")
        .order_by("created_at")
    )
    assert list(lifecycle_audits.values_list("metadata", flat=True)) == [
        {"from_status": "draft", "to_status": "archived"},
        {"from_status": "archived", "to_status": "draft"},
        {"from_status": "active", "to_status": "completed"},
        {"from_status": "completed", "to_status": "active"},
        {"from_status": "active", "to_status": "archived"},
        {"from_status": "archived", "to_status": "active"},
        {"from_status": "active", "to_status": "completed"},
        {"from_status": "completed", "to_status": "archived"},
        {"from_status": "archived", "to_status": "completed"},
    ]


@pytest.mark.django_db
def test_lifecycle_services_reject_wrong_roles_and_invalid_transitions():
    from apps.projects.models import ProjectMember
    from apps.projects.services import (
        ProjectNotFoundError,
        ProjectPermissionError,
        ProjectStateConflictError,
        archive_project,
        complete_project,
        create_project,
        reopen_project,
        restore_project,
    )

    executor = get_user_model().objects.create_user(email="lifecycle-owner@example.com")
    customer = get_user_model().objects.create_user(
        email="lifecycle-customer@example.com"
    )
    outsider = get_user_model().objects.create_user(
        email="lifecycle-outsider@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Draft project", "project_type": "website"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )

    with pytest.raises(ProjectPermissionError):
        archive_project(project_id=project.pk, actor=customer)
    with pytest.raises(ProjectNotFoundError):
        archive_project(project_id=project.pk, actor=outsider)
    with pytest.raises(ProjectStateConflictError):
        complete_project(project_id=project.pk, actor=executor)
    with pytest.raises(ProjectStateConflictError):
        reopen_project(project_id=project.pk, actor=executor)
    with pytest.raises(ProjectStateConflictError):
        restore_project(project_id=project.pk, actor=executor)

    archive_project(project_id=project.pk, actor=executor)
    with pytest.raises(ProjectStateConflictError):
        archive_project(project_id=project.pk, actor=executor)


@pytest.mark.django_db
def test_passport_update_uses_expected_version_and_audits_field_names_only():
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import ProjectPassport
    from apps.projects.services import (
        ProjectPassportVersionConflictError,
        create_project,
        update_passport,
    )

    executor = get_user_model().objects.create_user(email="passport-owner@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Passport", "project_type": "website"},
    )

    updated = update_passport(
        project_id=project.pk,
        actor=executor,
        expected_version=1,
        changes={"goal": "Launch a public website", "currency": "USD"},
    )

    assert updated.version == 2
    assert updated.goal == "Launch a public website"
    assert updated.currency == "USD"
    audit = ProjectAuditLog.objects.get(
        project=project,
        action="project.passport_updated",
    )
    assert audit.metadata == {
        "changed_fields": ["currency", "goal"],
        "previous_version": 1,
        "version": 2,
    }
    assert "Launch a public website" not in str(audit.metadata)

    with pytest.raises(ProjectPassportVersionConflictError):
        update_passport(
            project_id=project.pk,
            actor=executor,
            expected_version=1,
            changes={"goal": "Stale replacement"},
        )

    passport = ProjectPassport.objects.get(project=project)
    assert passport.goal == "Launch a public website"
    assert passport.version == 2
    assert (
        ProjectAuditLog.objects.filter(
            project=project,
            action="project.passport_updated",
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_passport_updates_with_same_version_only_commit_once():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    from apps.projects.models import ProjectPassport
    from apps.projects.services import (
        ProjectPassportVersionConflictError,
        create_project,
        update_passport,
    )

    executor = get_user_model().objects.create_user(email="passport-race@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Concurrent passport", "project_type": "website"},
    )
    barrier = Barrier(2)

    def update_goal(value):
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            update_passport(
                project_id=project.pk,
                actor=executor,
                expected_version=1,
                changes={"goal": value},
            )
            return "updated"
        except ProjectPassportVersionConflictError:
            return "stale"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor_pool:
        outcomes = list(executor_pool.map(update_goal, ("First", "Second")))

    assert sorted(outcomes) == ["stale", "updated"]
    passport = ProjectPassport.objects.get(project=project)
    assert passport.version == 2
    assert passport.goal in {"First", "Second"}


@pytest.mark.django_db
def test_passport_update_rolls_back_when_audit_write_fails(monkeypatch):
    from apps.projects.models import ProjectPassport
    from apps.projects.services import create_project, update_passport

    executor = get_user_model().objects.create_user(
        email="passport-audit-fail@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Audit rollback", "project_type": "website"},
    )

    def fail_audit(**_kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr("apps.projects.services.record_project_action", fail_audit)
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        update_passport(
            project_id=project.pk,
            actor=executor,
            expected_version=1,
            changes={"goal": "Must roll back"},
        )

    passport = ProjectPassport.objects.get(project=project)
    assert passport.goal == ""
    assert passport.version == 1


@pytest.mark.django_db
def test_lifecycle_transition_rolls_back_when_audit_write_fails(monkeypatch):
    from apps.projects.services import archive_project, create_project

    executor = get_user_model().objects.create_user(
        email="lifecycle-audit-fail@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Audit rollback", "project_type": "website"},
    )

    def fail_audit(**_kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr("apps.projects.services.record_project_action", fail_audit)
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        archive_project(project_id=project.pk, actor=executor)

    project.refresh_from_db()
    assert project.status == "draft"
    assert project.status_before_archive is None
    assert project.archived_at is None


@pytest.mark.django_db
def test_invitation_service_adds_customer_and_activates_draft_atomically():
    from django.utils import timezone

    from apps.common.models import ProjectAuditLog
    from apps.projects.services import (
        add_customer_member_from_invitation,
        create_project,
    )

    executor = get_user_model().objects.create_user(email="invite-owner@example.com")
    customer = get_user_model().objects.create_user(
        email="invite-customer@example.com",
        email_verified_at=timezone.now(),
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation acceptance", "project_type": "website"},
    )

    membership = add_customer_member_from_invitation(
        project_id=project.pk,
        user=customer,
    )

    project.refresh_from_db()
    assert project.status == "active"
    assert (membership.project_id, membership.user_id) == (project.pk, customer.pk)
    assert (membership.role, membership.status) == ("customer", "active")
    audit = ProjectAuditLog.objects.get(
        project=project,
        action="project.customer_joined",
    )
    assert audit.target_id == str(membership.pk)
    assert audit.metadata == {"from_status": "draft", "to_status": "active"}


@pytest.mark.django_db
def test_questionnaire_mapping_is_customer_owned_versioned_and_audited():
    from django.utils import timezone

    from apps.common.models import ProjectAuditLog
    from apps.projects.models import ProjectMember, ProjectPassport
    from apps.projects.services import (
        ProjectPassportVersionConflictError,
        apply_questionnaire_mapping,
        create_project,
    )

    executor = get_user_model().objects.create_user(
        email="questionnaire-owner@example.com"
    )
    customer = get_user_model().objects.create_user(
        email="questionnaire-customer@example.com"
    )
    customer.email_verified_at = timezone.now()
    customer.save(update_fields=["email_verified_at"])
    project = create_project(
        actor=executor,
        data={"name": "Questionnaire mapping", "project_type": "website"},
    )
    project.status = "active"
    project.save(update_fields=["status", "updated_at"])
    ProjectMember.objects.create(project=project, user=customer, role="customer")

    passport = apply_questionnaire_mapping(
        project_id=project.pk,
        actor=customer,
        expected_version=1,
        mapped_changes={
            "goal": "Customer goal",
            "functional_scope": {"website": "New account workflow"},
        },
    )

    assert passport.version == 2
    assert passport.goal == "Customer goal"
    assert passport.functional_scope == {"website": "New account workflow"}
    audit = ProjectAuditLog.objects.get(
        project=project,
        action="project.questionnaire_mapped",
    )
    assert audit.actor_id == customer.pk
    assert audit.metadata == {
        "changed_fields": ["functional_scope", "goal"],
        "previous_version": 1,
        "version": 2,
    }
    assert "Customer goal" not in str(audit.metadata)

    with pytest.raises(ProjectPassportVersionConflictError):
        apply_questionnaire_mapping(
            project_id=project.pk,
            actor=customer,
            expected_version=1,
            mapped_changes={"goal": "Stale customer goal"},
        )
    assert ProjectPassport.objects.get(project=project).goal == "Customer goal"


@pytest.mark.django_db
def test_questionnaire_mapping_rejects_invalid_actor_and_fields():
    from django.core.exceptions import ValidationError
    from django.utils import timezone

    from apps.projects.models import ProjectMember
    from apps.projects.services import (
        ProjectPermissionError,
        apply_questionnaire_mapping,
        create_project,
    )

    executor = get_user_model().objects.create_user(email="map-executor@example.com")
    customer = get_user_model().objects.create_user(email="map-customer@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Questionnaire mapping access", "project_type": "website"},
    )
    project.status = "active"
    project.save(update_fields=["status", "updated_at"])
    ProjectMember.objects.create(project=project, user=customer, role="customer")

    with pytest.raises(ProjectPermissionError):
        apply_questionnaire_mapping(
            project_id=project.pk,
            actor=executor,
            expected_version=1,
            mapped_changes={"goal": "Executor bypass"},
        )
    with pytest.raises(ProjectPermissionError):
        apply_questionnaire_mapping(
            project_id=project.pk,
            actor=customer,
            expected_version=1,
            mapped_changes={"goal": "Unverified customer"},
        )
    customer.email_verified_at = timezone.now()
    customer.save(update_fields=["email_verified_at"])
    with pytest.raises(ValidationError):
        apply_questionnaire_mapping(
            project_id=project.pk,
            actor=customer,
            expected_version=1,
            mapped_changes={"status": "completed"},
        )
