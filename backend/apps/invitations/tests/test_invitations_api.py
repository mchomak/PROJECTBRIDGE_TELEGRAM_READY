import hashlib
from datetime import timedelta

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.models import ProjectAuditLog
from apps.invitations import services as invitation_services
from apps.invitations.models import ProjectInvitation
from apps.projects.models import Project, ProjectMember, ProjectMemberRole
from apps.projects.services import archive_project, complete_project, create_project


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_executor_can_create_project_invitation():
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation project", "project_type": "website"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)

    response = client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["invited_email"] == "customer@example.com"
    assert response.data["status"] == "pending"
    assert "token" not in response.data
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["customer@example.com"]
    assert "/invite/#token=" in mail.outbox[0].body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_executor_can_create_project_invitation_when_project_is_active():
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation project", "project_type": "website"},
    )
    Project.objects.filter(pk=project.pk).update(status="active")
    client = APIClient()
    client.force_authenticate(user=executor)

    response = client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == "pending"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_invitation_normalizes_email_hashes_token_and_keeps_audit_metadata_safe():
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation project", "project_type": "website"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    before_create = timezone.now()

    response = client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "  Customer@Example.COM  "},
        format="json",
    )

    after_create = timezone.now()
    assert response.status_code == 201
    assert response.data["invited_email"] == "customer@example.com"
    invitation = ProjectInvitation.objects.get(pk=response.data["id"])
    assert invitation.invited_email == "customer@example.com"
    invitation_link = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    )
    raw_token = invitation_link.split("#token=", maxsplit=1)[1]
    assert (
        invitation.token_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    )
    assert raw_token not in response.content.decode()
    assert not hasattr(invitation, "token")
    assert before_create + timedelta(days=7) <= invitation.expires_at
    assert invitation.expires_at <= after_create + timedelta(days=7)

    audit = ProjectAuditLog.objects.get(action="project.invitation_created")
    assert audit.target_id == str(invitation.pk)
    assert audit.metadata == {}
    assert "customer@example.com" not in str(audit.metadata)
    assert raw_token not in str(audit.metadata)


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_only_the_project_executor_can_list_create_or_revoke_invitations():
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    customer = User.objects.create_user(
        "customer@example.com", password="test-password"
    )
    other_executor = User.objects.create_user(
        "other@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation project", "project_type": "website"},
    )
    foreign_project = create_project(
        actor=other_executor,
        data={"name": "Other project", "project_type": "website"},
    )
    creator = APIClient()
    creator.force_authenticate(user=executor)
    invitation_response = creator.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    assert invitation_response.status_code == 201
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
    )

    customer_client = APIClient()
    customer_client.force_authenticate(user=customer)
    assert (
        customer_client.get(f"/api/v1/projects/{project.pk}/invitations/").status_code
        == 403
    )
    assert (
        customer_client.post(
            f"/api/v1/projects/{project.pk}/invitations/",
            {"invited_email": "another@example.com"},
            format="json",
        ).status_code
        == 403
    )
    assert (
        customer_client.post(
            f"/api/v1/projects/{project.pk}/invitations/{invitation_response.data['id']}/revoke/"
        ).status_code
        == 403
    )

    foreign_client = APIClient()
    foreign_client.force_authenticate(user=other_executor)
    assert (
        foreign_client.get(f"/api/v1/projects/{project.pk}/invitations/").status_code
        == 404
    )
    assert (
        foreign_client.get(
            f"/api/v1/projects/{foreign_project.pk}/invitations/"
        ).status_code
        == 200
    )


@pytest.mark.parametrize("project_status", ["completed", "archived"])
@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_closed_project_rejects_invitation_creation_and_revocation(project_status):
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation project", "project_type": "website"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    invitation_response = client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    assert invitation_response.status_code == 201

    if project_status == "completed":
        Project.objects.filter(pk=project.pk).update(status="active")
        complete_project(project_id=project.pk, actor=executor)
    else:
        archive_project(project_id=project.pk, actor=executor)

    assert (
        client.post(
            f"/api/v1/projects/{project.pk}/invitations/",
            {"invited_email": "another@example.com"},
            format="json",
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/projects/{project.pk}/invitations/{invitation_response.data['id']}/revoke/"
        ).status_code
        == 409
    )


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_project_with_active_customer_cannot_receive_another_invitation():
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    customer = User.objects.create_user(
        "customer@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation project", "project_type": "website"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
    )
    client = APIClient()
    client.force_authenticate(user=executor)

    response = client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "another@example.com"},
        format="json",
    )

    assert response.status_code == 409
    assert ProjectInvitation.objects.filter(project=project).count() == 0
    assert mail.outbox == []


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_expired_invitation_is_listed_as_expired_and_email_can_be_invited_again():
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation project", "project_type": "website"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    invitation_url = f"/api/v1/projects/{project.pk}/invitations/"
    created = client.post(
        invitation_url,
        {"invited_email": "customer@example.com"},
        format="json",
    )
    invitation = ProjectInvitation.objects.get(pk=created.data["id"])
    invitation.expires_at = timezone.now() - timedelta(seconds=1)
    invitation.save(update_fields=("expires_at", "updated_at"))

    listing = client.get(invitation_url)
    listed = {row["id"]: row for row in listing.data["results"]}
    assert listed[str(invitation.pk)]["status"] == "expired"
    invitation.refresh_from_db()
    assert invitation.status == "expired"

    second = client.post(
        invitation_url,
        {"invited_email": "CUSTOMER@example.com"},
        format="json",
    )
    assert second.status_code == 201
    assert second.data["status"] == "pending"
    assert ProjectInvitation.objects.filter(project=project).count() == 2


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_executor_can_revoke_only_a_pending_invitation():
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation project", "project_type": "website"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    created = client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    revoke_url = (
        f"/api/v1/projects/{project.pk}/invitations/{created.data['id']}/revoke/"
    )

    revoked = client.post(revoke_url)
    assert revoked.status_code == 200
    assert revoked.data["status"] == "revoked"
    invitation = ProjectInvitation.objects.get(pk=created.data["id"])
    assert invitation.revoked_at is not None
    audit = ProjectAuditLog.objects.get(action="project.invitation_revoked")
    assert audit.target_id == str(invitation.pk)
    assert audit.metadata == {}
    assert client.post(revoke_url).status_code == 409


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_invitation_creation_is_limited_to_twenty_per_executor_per_hour():
    cache.clear()
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Invitation project", "project_type": "website"},
    )
    client = APIClient()
    client.force_authenticate(user=executor)
    invitation_url = f"/api/v1/projects/{project.pk}/invitations/"
    responses = [
        client.post(
            invitation_url,
            {"invited_email": f"customer-{number}@example.com"},
            format="json",
        )
        for number in range(1, 22)
    ]

    assert all(response.status_code == 201 for response in responses[:20])
    assert responses[-1].status_code == 429
    assert ProjectInvitation.objects.filter(project=project).count() == 20
    assert len(mail.outbox) == 20


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_valid_invitation_preview_returns_only_safe_details():
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={
            "name": "Private project name",
            "project_type": "website",
            "description": "Private project description",
        },
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    created = executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]

    response = APIClient().post(
        "/api/v1/invitations/preview/",
        {"token": raw_token},
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {
        "project_name": "Private project name",
        "email_hint": "c***@example.com",
        "expires_at": created.data["expires_at"],
        "status": "pending",
    }
    assert "customer@example.com" not in response.content.decode()
    assert raw_token not in response.content.decode()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_verified_invited_user_accepts_and_activates_draft_project():
    from django.utils import timezone

    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    customer = User.objects.create_user(
        "customer@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    project = create_project(
        actor=executor,
        data={"name": "Customer project", "project_type": "website"},
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    created = executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    invitation = ProjectInvitation.objects.get(pk=created.data["id"])
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]
    customer_client = APIClient()
    customer_client.force_authenticate(user=customer)

    response = customer_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )

    assert response.status_code == 200
    assert response.data == {
        "invitation_id": str(invitation.pk),
        "project_id": str(project.pk),
        "status": "accepted",
    }
    project.refresh_from_db()
    invitation.refresh_from_db()
    assert project.status == "active"
    assert invitation.status == "accepted"
    assert invitation.accepted_by_id == customer.pk
    assert ProjectMember.objects.filter(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
        status="active",
    ).exists()
    customer_project = customer_client.get(f"/api/v1/projects/{project.pk}/")
    assert customer_project.status_code == 200
    assert customer_project.data["id"] == str(project.pk)
    assert customer_project.data["name"] == "Customer project"


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_verified_invited_user_accepts_active_project_without_retransitioning_it():
    from django.utils import timezone

    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    customer = User.objects.create_user(
        "customer@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    project = create_project(
        actor=executor,
        data={"name": "Active customer project", "project_type": "website"},
    )
    Project.objects.filter(pk=project.pk).update(status="active")
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    created = executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]
    customer_client = APIClient()
    customer_client.force_authenticate(user=customer)

    response = customer_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )

    assert response.status_code == 200
    project.refresh_from_db()
    assert project.status == "active"
    assert (
        ProjectMember.objects.filter(
            project=project,
            user=customer,
            role=ProjectMemberRole.CUSTOMER,
            status="active",
        ).count()
        == 1
    )
    assert ProjectAuditLog.objects.get(
        project=project,
        target_type="project_invitation",
        target_id=created.data["id"],
        action="project.invitation_accepted",
    )


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_acceptance_audit_failure_rolls_back_membership_and_project_activation(
    monkeypatch,
):
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    customer = User.objects.create_user(
        "customer@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    project = create_project(
        actor=executor,
        data={"name": "Atomic invitation project", "project_type": "website"},
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    created = executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    invitation = ProjectInvitation.objects.get(pk=created.data["id"])
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]
    original_record_action = invitation_services.record_project_action

    def fail_invitation_audit(**kwargs):
        if kwargs["action"] == "project.invitation_accepted":
            raise RuntimeError("simulated invitation audit failure")
        return original_record_action(**kwargs)

    monkeypatch.setattr(
        "apps.invitations.services.record_project_action",
        fail_invitation_audit,
    )
    customer_client = APIClient()
    customer_client.force_authenticate(user=customer)

    response = customer_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )

    assert response.status_code == 500
    project.refresh_from_db()
    invitation.refresh_from_db()
    assert project.status == "draft"
    assert invitation.status == "pending"
    assert not ProjectMember.objects.filter(
        project=project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
        status="active",
    ).exists()
    assert not ProjectAuditLog.objects.filter(
        project=project,
        action="project.customer_joined",
    ).exists()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_acceptance_rejects_unverified_and_mismatched_accounts_safely():
    from django.utils import timezone

    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    unverified = User.objects.create_user(
        "customer@example.com", password="test-password"
    )
    mismatched = User.objects.create_user(
        "other@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    project = create_project(
        actor=executor,
        data={"name": "Private customer project", "project_type": "website"},
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    created = executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]
    unverified_client = APIClient()
    unverified_client.force_authenticate(user=unverified)
    mismatched_client = APIClient()
    mismatched_client.force_authenticate(user=mismatched)

    unverified_response = unverified_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )
    mismatch_response = mismatched_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )

    assert (unverified_response.status_code, unverified_response.data["code"]) == (
        403,
        "email_unverified",
    )
    assert (mismatch_response.status_code, mismatch_response.data["code"]) == (
        403,
        "email_mismatch",
    )
    assert "customer@example.com" not in mismatch_response.content.decode()
    assert ProjectInvitation.objects.get(pk=created.data["id"]).status == "pending"
    assert (
        ProjectMember.objects.filter(
            project=project,
            role=ProjectMemberRole.CUSTOMER,
            status="active",
        ).count()
        == 0
    )


@pytest.mark.parametrize(
    ("invitation_state", "expected_code", "expected_status"),
    [
        ("expired", "invitation_expired", 410),
        ("revoked", "invitation_revoked", 410),
        ("completed", "project_completed", 409),
        ("archived", "project_archived", 409),
    ],
)
@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_unavailable_invitation_states_are_distinct_and_do_not_disclose_details(
    invitation_state, expected_code, expected_status
):
    from django.utils import timezone

    customer = User.objects.create_user(
        "customer@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={
            "name": "Private project name",
            "project_type": "website",
            "description": "Private project description",
        },
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    created = executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    invitation = ProjectInvitation.objects.get(pk=created.data["id"])
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]

    if invitation_state == "expired":
        invitation.expires_at = timezone.now() - timedelta(seconds=1)
        invitation.save(update_fields=("expires_at", "updated_at"))
    elif invitation_state == "revoked":
        executor_client.post(
            f"/api/v1/projects/{project.pk}/invitations/{invitation.pk}/revoke/"
        )
    elif invitation_state == "completed":
        Project.objects.filter(pk=project.pk).update(status="active")
        complete_project(project_id=project.pk, actor=executor)
    else:
        archive_project(project_id=project.pk, actor=executor)

    invalid_preview = APIClient().post(
        "/api/v1/invitations/preview/",
        {"token": "unknown-invitation-token"},
        format="json",
    )
    assert invalid_preview.status_code == 404
    assert invalid_preview.data["code"] == "not_found"
    assert "Private project name" not in invalid_preview.content.decode()
    preview = APIClient().post(
        "/api/v1/invitations/preview/",
        {"token": raw_token},
        format="json",
    )
    customer_client = APIClient()
    customer_client.force_authenticate(user=customer)
    acceptance = customer_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )

    assert (preview.status_code, preview.data["code"]) == (
        expected_status,
        expected_code,
    )
    assert (acceptance.status_code, acceptance.data["code"]) == (
        expected_status,
        expected_code,
    )
    assert "customer@example.com" not in preview.content.decode()
    assert raw_token not in preview.content.decode()
    assert ProjectMember.objects.filter(project=project, user=customer).count() == 0


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_replaying_accepted_invitation_returns_same_result_without_duplicate_writes():
    from django.utils import timezone

    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    customer = User.objects.create_user(
        "customer@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    project = create_project(
        actor=executor,
        data={"name": "Replay project", "project_type": "website"},
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    created = executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]
    customer_client = APIClient()
    customer_client.force_authenticate(user=customer)

    first = customer_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )
    replay = customer_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )

    assert first.status_code == replay.status_code == 200
    assert replay.data == first.data
    assert (
        ProjectMember.objects.filter(
            project=project,
            user=customer,
            role=ProjectMemberRole.CUSTOMER,
            status="active",
        ).count()
        == 1
    )
    assert (
        ProjectAuditLog.objects.filter(
            project=project,
            action="project.customer_joined",
        ).count()
        == 1
    )
    assert (
        ProjectAuditLog.objects.filter(
            project=project,
            action="project.invitation_accepted",
        ).count()
        == 1
    )
    assert ProjectInvitation.objects.get(pk=created.data["id"]).accepted_at is not None


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_acceptance_rejects_a_second_active_customer_without_partial_changes():
    from django.utils import timezone

    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    invited_customer = User.objects.create_user(
        "customer@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    existing_customer = User.objects.create_user(
        "existing@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    project = create_project(
        actor=executor,
        data={"name": "Single customer project", "project_type": "website"},
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    created = executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    invitation = ProjectInvitation.objects.get(pk=created.data["id"])
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]
    ProjectMember.objects.create(
        project=project,
        user=existing_customer,
        role=ProjectMemberRole.CUSTOMER,
        status="active",
    )
    invited_client = APIClient()
    invited_client.force_authenticate(user=invited_customer)

    response = invited_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )

    assert response.status_code == 409
    project.refresh_from_db()
    invitation.refresh_from_db()
    assert project.status == "draft"
    assert invitation.status == "pending"
    assert (
        ProjectMember.objects.filter(
            project=project,
            role=ProjectMemberRole.CUSTOMER,
            status="active",
        ).count()
        == 1
    )
    assert not ProjectMember.objects.filter(
        project=project,
        user=invited_customer,
    ).exists()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_acceptance_membership_is_scoped_to_the_invited_project():
    from django.utils import timezone

    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    other_executor = User.objects.create_user(
        "other-executor@example.com", password="test-password"
    )
    customer = User.objects.create_user(
        "customer@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    invited_project = create_project(
        actor=executor,
        data={"name": "Invited project", "project_type": "website"},
    )
    unrelated_project = create_project(
        actor=other_executor,
        data={"name": "Unrelated project", "project_type": "website"},
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    executor_client.post(
        f"/api/v1/projects/{invited_project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]
    customer_client = APIClient()
    customer_client.force_authenticate(user=customer)

    response = customer_client.post(
        "/api/v1/invitations/accept/",
        {"token": raw_token},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["project_id"] == str(invited_project.pk)
    assert ProjectMember.objects.filter(
        project=invited_project,
        user=customer,
        role=ProjectMemberRole.CUSTOMER,
        status="active",
    ).exists()
    assert not ProjectMember.objects.filter(
        project=unrelated_project,
        user=customer,
    ).exists()
    assert (
        customer_client.get(f"/api/v1/projects/{unrelated_project.pk}/").status_code
        == 404
    )


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_invitation_preview_is_limited_to_thirty_requests_per_ip_per_hour():
    cache.clear()
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    project = create_project(
        actor=executor,
        data={"name": "Rate limited preview", "project_type": "website"},
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]
    preview_client = APIClient()

    responses = [
        preview_client.post(
            "/api/v1/invitations/preview/",
            {"token": raw_token},
            format="json",
            REMOTE_ADDR="203.0.113.10",
        )
        for _ in range(31)
    ]
    other_ip = APIClient().post(
        "/api/v1/invitations/preview/",
        {"token": raw_token},
        format="json",
        REMOTE_ADDR="203.0.113.11",
    )

    assert all(response.status_code == 200 for response in responses[:30])
    assert (responses[-1].status_code, responses[-1].data["code"]) == (
        429,
        "throttled",
    )
    assert "rate limit" in responses[-1].data["detail"].lower()
    assert other_ip.status_code == 200


@pytest.mark.django_db
def test_invitation_acceptance_is_limited_to_ten_requests_per_user_per_hour():
    from django.utils import timezone

    cache.clear()
    customer = User.objects.create_user(
        "customer@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    client = APIClient()
    client.force_authenticate(user=customer)

    responses = [
        client.post(
            "/api/v1/invitations/accept/",
            {"token": f"unknown-token-{number}"},
            format="json",
        )
        for number in range(11)
    ]

    assert all(response.status_code == 404 for response in responses[:10])
    assert (responses[-1].status_code, responses[-1].data["code"]) == (
        429,
        "throttled",
    )


@pytest.mark.django_db(transaction=True)
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_concurrent_acceptance_of_one_invitation_is_idempotent(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections
    from django.utils import timezone

    cache.clear()
    executor = User.objects.create_user(
        "executor@example.com", password="test-password"
    )
    customer = User.objects.create_user(
        "customer@example.com",
        password="test-password",
        email_verified_at=timezone.now(),
    )
    project = create_project(
        actor=executor,
        data={"name": "Concurrent acceptance", "project_type": "website"},
    )
    executor_client = APIClient()
    executor_client.force_authenticate(user=executor)
    created = executor_client.post(
        f"/api/v1/projects/{project.pk}/invitations/",
        {"invited_email": "customer@example.com"},
        format="json",
    )
    raw_token = next(
        line.removeprefix("Accept the invitation: ")
        for line in mail.outbox[0].body.splitlines()
        if line.startswith("Accept the invitation: ")
    ).split("#token=", maxsplit=1)[1]

    barrier = Barrier(2)
    add_customer = invitation_services.add_customer_member_from_invitation

    def synchronized_add_customer(*, project_id, user):
        barrier.wait(timeout=10)
        return add_customer(project_id=project_id, user=user)

    monkeypatch.setattr(
        "apps.invitations.services.add_customer_member_from_invitation",
        synchronized_add_customer,
    )

    def accept_from_separate_connection():
        close_old_connections()
        client = APIClient()
        client.force_authenticate(user=User.objects.get(pk=customer.pk))
        response = client.post(
            "/api/v1/invitations/accept/",
            {"token": raw_token},
            format="json",
        )
        result = (response.status_code, response.data)
        close_old_connections()
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: accept_from_separate_connection(), range(2)))

    assert [status_code for status_code, _ in results] == [200, 200]
    assert results[0][1] == results[1][1]
    assert (
        ProjectMember.objects.filter(
            project=project,
            user=customer,
            role=ProjectMemberRole.CUSTOMER,
            status="active",
        ).count()
        == 1
    )
    assert (
        ProjectAuditLog.objects.filter(
            project=project,
            action="project.customer_joined",
        ).count()
        == 1
    )
    assert (
        ProjectAuditLog.objects.filter(
            project=project,
            action="project.invitation_accepted",
        ).count()
        == 1
    )
    assert ProjectInvitation.objects.get(pk=created.data["id"]).status == "accepted"
