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
