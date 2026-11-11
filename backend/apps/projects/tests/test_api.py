import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient


def test_anonymous_project_list_returns_shared_unauthenticated_envelope():
    response = APIClient().get("/api/v1/projects/")

    assert response.status_code == 401
    assert set(response.data) == {"code", "detail", "errors", "request_id"}
    assert response.data["code"] == "unauthenticated"


@pytest.mark.django_db
def test_anonymous_project_mutations_and_reads_return_shared_401_envelope():
    from apps.projects.services import create_project

    owner = get_user_model().objects.create_user(
        email="anonymous-test-owner@example.com"
    )
    project = create_project(
        actor=owner,
        data={"name": "Private project", "project_type": "website"},
    )
    client = APIClient()
    responses = (
        client.post(
            "/api/v1/projects/",
            {"name": "Anonymous", "project_type": "website"},
            format="json",
        ),
        client.get(f"/api/v1/projects/{project.pk}/"),
        client.patch(
            f"/api/v1/projects/{project.pk}/",
            {"name": "Anonymous write"},
            format="json",
        ),
        client.get(f"/api/v1/projects/{project.pk}/members/"),
        client.get(f"/api/v1/projects/{project.pk}/passport/"),
        client.patch(
            f"/api/v1/projects/{project.pk}/passport/",
            {"version": 1, "goal": "Anonymous"},
            format="json",
        ),
        client.post(f"/api/v1/projects/{project.pk}/complete/", {}, format="json"),
    )

    for response in responses:
        assert response.status_code == 401
        assert set(response.data) == {"code", "detail", "errors", "request_id"}
        assert response.data["code"] == "unauthenticated"


def _verified_user(email="executor@example.com"):
    user = get_user_model().objects.create_user(email=email)
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return user


def _authenticated_client(user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    csrf_response = client.get("/api/v1/auth/csrf/")
    return client, {"HTTP_X_CSRFTOKEN": csrf_response.data["csrf_token"]}


@pytest.mark.django_db
def test_verified_user_creates_project_with_initial_executor_data():
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import Project, ProjectMember, ProjectPassport

    user = _verified_user()
    client, csrf = _authenticated_client(user)

    response = client.post(
        "/api/v1/projects/",
        {
            "name": "Telegram launch",
            "project_type": "telegram_bot",
            "description": "First release",
        },
        format="json",
        **csrf,
    )

    assert response.status_code == 201
    assert set(response.data) == {
        "id",
        "name",
        "description",
        "project_type",
        "status",
        "created_at",
        "updated_at",
        "completed_at",
        "archived_at",
    }
    project = Project.objects.get(name="Telegram launch")
    assert response.data["id"] == str(project.pk)
    assert response.data["status"] == "draft"
    assert project.project_type == "telegram_bot"
    assert project.description == "First release"
    assert ProjectMember.objects.filter(
        project=project,
        user=user,
        role="executor",
        status="active",
    ).exists()
    assert ProjectPassport.objects.filter(project=project, version=1).exists()
    assert ProjectAuditLog.objects.filter(
        project=project,
        action="project.created",
    ).exists()


@pytest.mark.django_db
def test_unverified_user_cannot_create_a_project():
    from apps.projects.models import Project

    user = get_user_model().objects.create_user(email="unverified@example.com")
    client, csrf = _authenticated_client(user)

    response = client.post(
        "/api/v1/projects/",
        {"name": "Not allowed", "project_type": "website"},
        format="json",
        **csrf,
    )

    assert response.status_code == 403
    assert response.data["code"] == "permission_denied"
    assert Project.objects.count() == 0


@pytest.mark.parametrize(
    "project_type",
    ["website", "telegram_bot", "automation", "other"],
)
@pytest.mark.django_db
def test_verified_user_can_create_each_supported_project_type(project_type):
    from apps.projects.models import Project

    user = _verified_user(email=f"{project_type}@example.com")
    client, csrf = _authenticated_client(user)

    response = client.post(
        "/api/v1/projects/",
        {"name": "Supported type", "project_type": project_type},
        format="json",
        **csrf,
    )

    assert response.status_code == 201
    assert response.data["project_type"] == project_type
    assert Project.objects.get(pk=response.data["id"]).description is None


@pytest.mark.django_db
def test_project_creation_rejects_invalid_and_server_owned_fields():
    from apps.projects.models import Project

    user = _verified_user(email="invalid-create@example.com")
    client, csrf = _authenticated_client(user)
    invalid_payloads = (
        {"name": "", "project_type": "website"},
        {"name": "Invalid type", "project_type": "not-a-project-type"},
        {"name": "Server field", "project_type": "website", "status": "active"},
        {"project_type": "website"},
    )

    for payload in invalid_payloads:
        response = client.post(
            "/api/v1/projects/",
            payload,
            format="json",
            **csrf,
        )
        assert response.status_code == 400
        assert response.data["code"] == "validation_error"

    assert Project.objects.count() == 0


@pytest.mark.django_db
def test_project_creation_rejects_name_over_200_characters():
    from apps.projects.models import Project

    user = _verified_user(email="long-name-create@example.com")
    client, csrf = _authenticated_client(user)

    response = client.post(
        "/api/v1/projects/",
        {"name": "N" * 201, "project_type": "website"},
        format="json",
        **csrf,
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "name" in response.data["errors"]
    assert Project.objects.count() == 0


@pytest.mark.django_db
def test_project_creation_rejects_unknown_form_encoded_fields():
    from apps.projects.models import Project

    user = _verified_user(email="form-create-executor@example.com")
    client, csrf = _authenticated_client(user)

    response = client.post(
        "/api/v1/projects/",
        data="name=Forbidden&project_type=website&status=active",
        content_type="application/x-www-form-urlencoded",
        **csrf,
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "Unknown project fields were provided." in str(response.data["errors"])
    assert Project.objects.count() == 0


@pytest.mark.django_db
def test_project_list_scopes_active_members_and_filters_archives():
    from django.utils import timezone

    from apps.projects.models import Project, ProjectMember
    from apps.projects.services import create_project

    user = get_user_model().objects.create_user(email="member@example.com")
    other_user = get_user_model().objects.create_user(email="other@example.com")
    inactive_owner = get_user_model().objects.create_user(
        email="inactive-owner@example.com"
    )
    regular_project = create_project(
        actor=user,
        data={"name": "Regular", "project_type": "website"},
    )
    archived_project = create_project(
        actor=user,
        data={"name": "Archived", "project_type": "automation"},
    )
    foreign_project = create_project(
        actor=other_user,
        data={"name": "Foreign", "project_type": "other"},
    )
    inactive_project = create_project(
        actor=inactive_owner,
        data={"name": "Inactive membership", "project_type": "website"},
    )
    Project.objects.filter(pk=archived_project.pk).update(
        status="archived",
        status_before_archive="draft",
        archived_at=timezone.now(),
    )
    Project.objects.filter(pk=foreign_project.pk).update(
        status="archived",
        status_before_archive="draft",
        archived_at=timezone.now(),
    )
    ProjectMember.objects.create(
        project=inactive_project,
        user=user,
        role="customer",
        status="left",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    regular_response = client.get("/api/v1/projects/")
    archive_response = client.get("/api/v1/projects/?status=archived")

    assert regular_response.status_code == 200
    assert [item["id"] for item in regular_response.data["results"]] == [
        str(regular_project.pk)
    ]
    assert archive_response.status_code == 200
    assert [item["id"] for item in archive_response.data["results"]] == [
        str(archived_project.pk)
    ]


@pytest.mark.django_db
def test_active_members_read_archived_project_and_only_active_members():
    from django.utils import timezone

    from apps.projects.models import Project, ProjectMember
    from apps.projects.services import create_project

    executor = get_user_model().objects.create_user(
        email="archived-executor@example.com",
        first_name="Erin",
        last_name="Executor",
    )
    customer = get_user_model().objects.create_user(
        email="archived-customer@example.com",
        first_name="Casey",
        last_name="Customer",
    )
    former_member = get_user_model().objects.create_user(
        email="former-member@example.com"
    )
    outsider = get_user_model().objects.create_user(email="outsider@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Archived project", "project_type": "other"},
    )
    Project.objects.filter(pk=project.pk).update(
        status="archived",
        status_before_archive="active",
        archived_at=timezone.now(),
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )
    ProjectMember.objects.create(
        project=project,
        user=former_member,
        role="customer",
        status="left",
    )
    client = APIClient()
    client.force_authenticate(user=customer)

    detail_response = client.get(f"/api/v1/projects/{project.pk}/")
    members_response = client.get(f"/api/v1/projects/{project.pk}/members/")

    assert detail_response.status_code == 200
    assert detail_response.data["id"] == str(project.pk)
    assert detail_response.data["status"] == "archived"
    assert members_response.status_code == 200
    assert all(
        set(member) == {"id", "user_id", "role", "joined_at", "first_name", "last_name"}
        for member in members_response.data
    )
    assert {member["id"] for member in members_response.data} == {
        str(executor.pk),
        str(customer.pk),
    }
    assert {member["role"] for member in members_response.data} == {
        "executor",
        "customer",
    }

    for user in (former_member, outsider):
        client.force_authenticate(user=user)
        assert client.get(f"/api/v1/projects/{project.pk}/").status_code == 404
        assert client.get(f"/api/v1/projects/{project.pk}/members/").status_code == 404


@pytest.mark.django_db
def test_project_list_pagination_bounds_order_and_status_validation():
    from uuid import UUID

    from django.utils import timezone

    from apps.projects.models import Project, ProjectMember

    user = get_user_model().objects.create_user(email="pagination@example.com")
    now = timezone.now()
    project_ids = [UUID(int=index) for index in range(1, 102)]
    Project.objects.bulk_create(
        [
            Project(
                id=project_id,
                name=f"Project {index}",
                project_type="website",
                created_by=user,
                created_at=now,
                updated_at=now,
            )
            for index, project_id in enumerate(project_ids, start=1)
        ]
    )
    Project.objects.all().update(updated_at=now)
    ProjectMember.objects.bulk_create(
        [
            ProjectMember(
                project_id=project_id,
                user=user,
                role="executor",
                status="active",
                joined_at=now,
            )
            for project_id in project_ids
        ]
    )
    client = APIClient()
    client.force_authenticate(user=user)

    first_page = client.get("/api/v1/projects/")
    oversized_page = client.get("/api/v1/projects/?page_size=500")
    invalid_status = client.get("/api/v1/projects/?status=active")

    assert first_page.status_code == 200
    assert first_page.data["count"] == 101
    assert [item["id"] for item in first_page.data["results"]] == [
        str(project_id) for project_id in project_ids[:20]
    ]
    assert "page=2" in first_page.data["next"]
    assert len(oversized_page.data["results"]) == 100
    assert oversized_page.data["count"] == 101
    assert invalid_status.status_code == 400
    assert invalid_status.data["code"] == "validation_error"
    assert "status" in invalid_status.data["errors"]


@pytest.mark.django_db
def test_executor_metadata_patch_returns_project_and_audits_changed_fields_only():
    from apps.common.models import ProjectAuditLog
    from apps.projects.services import create_project

    user = _verified_user(email="metadata-executor@example.com")
    project = create_project(
        actor=user,
        data={
            "name": "Before",
            "project_type": "website",
            "description": "Before description",
        },
    )
    client, csrf = _authenticated_client(user)

    response = client.patch(
        f"/api/v1/projects/{project.pk}/",
        {"name": "After", "description": "After description"},
        format="json",
        **csrf,
    )

    assert response.status_code == 200
    assert response.data["name"] == "After"
    assert response.data["description"] == "After description"
    project.refresh_from_db()
    assert project.name == "After"
    assert project.description == "After description"
    audit = ProjectAuditLog.objects.get(
        project=project,
        action="project.metadata_updated",
    )
    assert audit.metadata == {"changed_fields": ["description", "name"]}
    assert "After" not in str(audit.metadata)


@pytest.mark.django_db
def test_metadata_patch_rejects_name_over_200_characters():
    from apps.projects.services import create_project

    executor = _verified_user(email="long-name-patch@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Before", "project_type": "website"},
    )
    client, csrf = _authenticated_client(executor)

    response = client.patch(
        f"/api/v1/projects/{project.pk}/",
        {"name": "N" * 201},
        format="json",
        **csrf,
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "name" in response.data["errors"]
    project.refresh_from_db()
    assert project.name == "Before"


@pytest.mark.django_db
def test_metadata_patch_rejects_unknown_form_encoded_fields():
    from apps.projects.services import create_project

    executor = _verified_user(email="form-patch-executor@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Before", "project_type": "website"},
    )
    client, csrf = _authenticated_client(executor)

    response = client.patch(
        f"/api/v1/projects/{project.pk}/",
        data="name=Changed&status=completed",
        content_type="application/x-www-form-urlencoded",
        **csrf,
    )

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "Unknown project fields were provided." in str(response.data["errors"])
    project.refresh_from_db()
    assert project.name == "Before"
    assert project.status == "draft"


@pytest.mark.django_db
def test_metadata_patch_enforces_role_membership_state_and_server_fields():
    from django.utils import timezone

    from apps.projects.models import Project, ProjectMember
    from apps.projects.services import create_project

    executor = get_user_model().objects.create_user(email="patch-executor@example.com")
    customer = get_user_model().objects.create_user(email="patch-customer@example.com")
    former_member = get_user_model().objects.create_user(
        email="patch-former@example.com"
    )
    outsider = get_user_model().objects.create_user(email="patch-outsider@example.com")
    draft_project = create_project(
        actor=executor,
        data={"name": "Draft", "project_type": "website"},
    )
    active_project = create_project(
        actor=executor,
        data={"name": "Active", "project_type": "website"},
    )
    completed_project = create_project(
        actor=executor,
        data={"name": "Completed", "project_type": "website"},
    )
    archived_project = create_project(
        actor=executor,
        data={"name": "Archived", "project_type": "website"},
    )
    Project.objects.filter(pk=active_project.pk).update(status="active")
    Project.objects.filter(pk=completed_project.pk).update(
        status="completed",
        completed_at=timezone.now(),
    )
    Project.objects.filter(pk=archived_project.pk).update(
        status="archived",
        status_before_archive="draft",
        archived_at=timezone.now(),
    )
    ProjectMember.objects.create(
        project=draft_project,
        user=customer,
        role="customer",
        status="active",
    )
    ProjectMember.objects.create(
        project=draft_project,
        user=former_member,
        role="customer",
        status="left",
    )

    active_client, active_csrf = _authenticated_client(executor)
    active_response = active_client.patch(
        f"/api/v1/projects/{active_project.pk}/",
        {"project_type": "automation"},
        format="json",
        **active_csrf,
    )
    customer_client, customer_csrf = _authenticated_client(customer)
    customer_response = customer_client.patch(
        f"/api/v1/projects/{draft_project.pk}/",
        {"name": "Customer write"},
        format="json",
        **customer_csrf,
    )
    completed_client, completed_csrf = _authenticated_client(executor)
    completed_response = completed_client.patch(
        f"/api/v1/projects/{completed_project.pk}/",
        {"name": "Completed write"},
        format="json",
        **completed_csrf,
    )
    archived_client, archived_csrf = _authenticated_client(executor)
    archived_response = archived_client.patch(
        f"/api/v1/projects/{archived_project.pk}/",
        {"name": "Archived write"},
        format="json",
        **archived_csrf,
    )
    server_field_response = active_client.patch(
        f"/api/v1/projects/{active_project.pk}/",
        {"status": "completed"},
        format="json",
        **active_csrf,
    )
    former_client, former_csrf = _authenticated_client(former_member)
    former_response = former_client.patch(
        f"/api/v1/projects/{draft_project.pk}/",
        {"name": "Former member write"},
        format="json",
        **former_csrf,
    )
    outsider_client, outsider_csrf = _authenticated_client(outsider)
    outsider_response = outsider_client.patch(
        f"/api/v1/projects/{draft_project.pk}/",
        {"name": "Foreign write"},
        format="json",
        **outsider_csrf,
    )

    assert active_response.status_code == 200
    assert active_response.data["project_type"] == "automation"
    assert customer_response.status_code == 403
    assert completed_response.status_code == 409
    assert archived_response.status_code == 409
    assert server_field_response.status_code == 400
    assert former_response.status_code == 404
    assert outsider_response.status_code == 404
    draft_project.refresh_from_db()
    completed_project.refresh_from_db()
    archived_project.refresh_from_db()
    assert draft_project.name == "Draft"
    assert completed_project.name == "Completed"
    assert archived_project.name == "Archived"


@pytest.mark.parametrize("project_status", ["draft", "active", "completed", "archived"])
@pytest.mark.django_db
def test_active_project_members_can_read_exact_passport_fields_in_every_status(
    project_status,
):
    from apps.projects.models import Project, ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    executor = get_user_model().objects.create_user(
        email=f"passport-reader-executor-{project_status}@example.com"
    )
    customer = get_user_model().objects.create_user(
        email=f"passport-reader-customer-{project_status}@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Readable passport", "project_type": "website"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )
    status_values = {"status": project_status}
    if project_status == "completed":
        status_values["completed_at"] = timezone.now()
    elif project_status == "archived":
        status_values.update(
            status_before_archive="active",
            archived_at=timezone.now(),
        )
    Project.objects.filter(pk=project.pk).update(**status_values)
    expected_fields = {
        "id",
        "project_id",
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

    for participant in (executor, customer):
        client = APIClient()
        client.force_authenticate(user=participant)
        response = client.get(f"/api/v1/projects/{project.pk}/passport/")
        assert response.status_code == 200
        assert set(response.data) == expected_fields
        assert response.data["project_id"] == str(project.pk)
        assert response.data["version"] == 1
        assert response.data["goal"] == ""
        assert response.data["functional_scope"] == {}

    assert ProjectPassport.objects.filter(project=project).exists()


@pytest.mark.django_db
def test_project_passport_read_and_update_are_scoped_to_active_membership():
    from apps.projects.models import ProjectMember
    from apps.projects.services import create_project

    executor = get_user_model().objects.create_user(
        email="passport-scope-owner@example.com"
    )
    former_member = get_user_model().objects.create_user(
        email="passport-scope-former@example.com"
    )
    outsider = get_user_model().objects.create_user(
        email="passport-scope-outsider@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Private passport", "project_type": "other"},
    )
    ProjectMember.objects.create(
        project=project,
        user=former_member,
        role="customer",
        status="left",
    )

    for user in (former_member, outsider):
        client, csrf = _authenticated_client(user)
        read_response = client.get(f"/api/v1/projects/{project.pk}/passport/")
        write_response = client.patch(
            f"/api/v1/projects/{project.pk}/passport/",
            {"version": 1, "goal": "Unauthorized"},
            format="json",
            **csrf,
        )
        assert read_response.status_code == 404
        assert write_response.status_code == 404
        assert read_response.data["code"] == "not_found"
        assert write_response.data["code"] == "not_found"


@pytest.mark.django_db
def test_executor_passport_patch_updates_exact_fields_and_audits_no_values():
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import ProjectPassport
    from apps.projects.services import create_project

    executor = _verified_user(email="passport-patch-executor@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Passport update", "project_type": "automation"},
    )
    client, csrf = _authenticated_client(executor)

    response = client.patch(
        f"/api/v1/projects/{project.pk}/passport/",
        {
            "version": 1,
            "goal": "",
            "target_audience": "Operations teams",
            "expected_result": "Fewer manual steps",
            "functional_scope": ["daily report"],
            "integrations": {"service": "mail"},
            "constraints": {"region": "EU"},
            "deadline": "2026-12-01",
            "budget_min": "1000.25",
            "budget_max": "2000",
            "currency": "usd",
            "additional_data": {"source": "client supplied"},
        },
        format="json",
        **csrf,
    )

    assert response.status_code == 200
    assert response.data["version"] == 2
    assert response.data["goal"] == ""
    assert response.data["currency"] == "USD"
    assert response.data["deadline"] == "2026-12-01"
    assert response.data["budget_min"] == "1000.2500000000"
    assert response.data["functional_scope"] == ["daily report"]
    passport = ProjectPassport.objects.get(project=project)
    assert passport.version == 2
    assert passport.additional_data == {"source": "client supplied"}
    audit = ProjectAuditLog.objects.get(
        project=project,
        action="project.passport_updated",
    )
    assert audit.metadata == {
        "changed_fields": [
            "additional_data",
            "budget_max",
            "budget_min",
            "constraints",
            "currency",
            "deadline",
            "expected_result",
            "functional_scope",
            "goal",
            "integrations",
            "target_audience",
        ],
        "previous_version": 1,
        "version": 2,
    }
    assert "Operations teams" not in str(audit.metadata)
    assert "client supplied" not in str(audit.metadata)


@pytest.mark.django_db
def test_passport_patch_requires_version_and_field_rejects_unknown_or_invalid_data():
    from apps.projects.models import ProjectPassport
    from apps.projects.services import create_project

    executor = _verified_user(email="passport-validation@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Passport validation", "project_type": "website"},
    )
    client, csrf = _authenticated_client(executor)
    invalid_payloads = (
        {"goal": "Missing version"},
        {"version": 1},
        {"version": 1, "project_id": str(project.pk), "goal": "No"},
        {"version": 1, "goal": "Invalid currency", "currency": "U$D"},
        {"version": 1, "goal": "Invalid deadline", "deadline": "not-a-date"},
        {"version": 1, "goal": "Invalid JSON", "functional_scope": None},
    )

    for payload in invalid_payloads:
        response = client.patch(
            f"/api/v1/projects/{project.pk}/passport/",
            payload,
            format="json",
            **csrf,
        )
        assert response.status_code == 400
        assert response.data["code"] == "validation_error"

    passport = ProjectPassport.objects.get(project=project)
    assert passport.version == 1
    assert passport.goal == ""


def test_passport_patch_openapi_requires_positive_version_and_keeps_fields_optional():
    from drf_spectacular.generators import SchemaGenerator

    schema = SchemaGenerator().get_schema(request=None, public=True)
    operation = schema["paths"]["/api/v1/projects/{project_id}/passport/"]["patch"]
    request_body = operation["requestBody"]
    assert request_body["required"] is True

    request_schema = request_body["content"]["application/json"]["schema"]
    request_schema = schema["components"]["schemas"][
        request_schema["$ref"].rsplit("/", maxsplit=1)[-1]
    ]
    assert request_schema["required"] == ["version"]
    assert request_schema["properties"]["version"] == {
        "type": "integer",
        "minimum": 1,
    }
    passport_fields = {
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
    }
    assert passport_fields <= request_schema["properties"].keys()
    assert passport_fields.isdisjoint(request_schema["required"])


@pytest.mark.django_db
def test_customer_cannot_patch_passport_while_project_is_editable():
    from apps.projects.models import ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    executor = get_user_model().objects.create_user(
        email="passport-role-owner@example.com"
    )
    customer = get_user_model().objects.create_user(
        email="passport-role-customer@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Customer cannot edit", "project_type": "website"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )
    client, csrf = _authenticated_client(customer)

    response = client.patch(
        f"/api/v1/projects/{project.pk}/passport/",
        {"version": 1, "goal": "Customer supplied"},
        format="json",
        **csrf,
    )

    assert response.status_code == 403
    assert response.data["code"] == "permission_denied"
    passport = ProjectPassport.objects.get(project=project)
    assert passport.goal == ""
    assert passport.version == 1


@pytest.mark.django_db
def test_stale_passport_patch_returns_409_without_overwriting_or_auditing_again():
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import ProjectPassport
    from apps.projects.services import create_project

    executor = _verified_user(email="passport-stale@example.com")
    project = create_project(
        actor=executor,
        data={"name": "Passport stale", "project_type": "website"},
    )
    client, csrf = _authenticated_client(executor)
    first_response = client.patch(
        f"/api/v1/projects/{project.pk}/passport/",
        {"version": 1, "goal": "Newest value"},
        format="json",
        **csrf,
    )
    stale_response = client.patch(
        f"/api/v1/projects/{project.pk}/passport/",
        {"version": 1, "goal": "Stale overwrite"},
        format="json",
        **csrf,
    )

    assert first_response.status_code == 200
    assert first_response.data["version"] == 2
    assert stale_response.status_code == 409
    assert stale_response.data["code"] == "conflict"
    passport = ProjectPassport.objects.get(project=project)
    assert passport.goal == "Newest value"
    assert passport.version == 2
    assert (
        ProjectAuditLog.objects.filter(
            project=project,
            action="project.passport_updated",
        ).count()
        == 1
    )


@pytest.mark.parametrize("project_status", ["completed", "archived"])
@pytest.mark.django_db
def test_passport_is_read_only_for_every_role_after_completion_or_archive(
    project_status,
):
    from apps.projects.models import Project, ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    executor = get_user_model().objects.create_user(
        email=f"passport-readonly-executor-{project_status}@example.com"
    )
    customer = get_user_model().objects.create_user(
        email=f"passport-readonly-customer-{project_status}@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Read-only passport", "project_type": "website"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )
    status_values = {"status": project_status}
    if project_status == "completed":
        status_values["completed_at"] = timezone.now()
    else:
        status_values.update(
            status_before_archive="active",
            archived_at=timezone.now(),
        )
    Project.objects.filter(pk=project.pk).update(**status_values)

    executor_client, executor_csrf = _authenticated_client(executor)
    customer_client, customer_csrf = _authenticated_client(customer)
    executor_response = executor_client.patch(
        f"/api/v1/projects/{project.pk}/passport/",
        {"version": 1, "goal": "No write"},
        format="json",
        **executor_csrf,
    )
    customer_response = customer_client.patch(
        f"/api/v1/projects/{project.pk}/passport/",
        {"version": 1, "goal": "No write"},
        format="json",
        **customer_csrf,
    )

    assert executor_response.status_code == 409
    assert customer_response.status_code == 403
    passport = ProjectPassport.objects.get(project=project)
    assert passport.goal == ""
    assert passport.version == 1


@pytest.mark.django_db
def test_lifecycle_actions_enforce_actor_and_source_status_and_preserve_data():
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import Project, ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    executor = get_user_model().objects.create_user(
        email="lifecycle-api-owner@example.com"
    )
    customer = get_user_model().objects.create_user(
        email="lifecycle-api-customer@example.com"
    )
    outsider = get_user_model().objects.create_user(
        email="lifecycle-api-outsider@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Lifecycle API", "project_type": "website"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )
    executor_client, executor_csrf = _authenticated_client(executor)
    customer_client, customer_csrf = _authenticated_client(customer)
    outsider_client, outsider_csrf = _authenticated_client(outsider)

    complete_from_draft = executor_client.post(
        f"/api/v1/projects/{project.pk}/complete/",
        {},
        format="json",
        **executor_csrf,
    )
    reopen_from_draft = executor_client.post(
        f"/api/v1/projects/{project.pk}/reopen/",
        {},
        format="json",
        **executor_csrf,
    )
    restore_from_draft = executor_client.post(
        f"/api/v1/projects/{project.pk}/restore/",
        {},
        format="json",
        **executor_csrf,
    )
    customer_archive = customer_client.post(
        f"/api/v1/projects/{project.pk}/archive/",
        {},
        format="json",
        **customer_csrf,
    )
    outsider_archive = outsider_client.post(
        f"/api/v1/projects/{project.pk}/archive/",
        {},
        format="json",
        **outsider_csrf,
    )

    assert complete_from_draft.status_code == 409
    assert reopen_from_draft.status_code == 409
    assert restore_from_draft.status_code == 409
    assert customer_archive.status_code == 403
    assert outsider_archive.status_code == 404

    archived = executor_client.post(
        f"/api/v1/projects/{project.pk}/archive/",
        {},
        format="json",
        **executor_csrf,
    )
    assert archived.status_code == 200
    assert archived.data["status"] == "archived"
    assert "status_before_archive" not in archived.data
    project.refresh_from_db()
    assert project.status_before_archive == "draft"
    assert project.archived_at is not None
    assert ProjectMember.objects.filter(project=project).count() == 2
    assert ProjectPassport.objects.filter(project=project).exists()
    assert executor_client.get("/api/v1/projects/").data["count"] == 0
    assert executor_client.get("/api/v1/projects/?status=archived").data["count"] == 1

    restored = executor_client.post(
        f"/api/v1/projects/{project.pk}/restore/",
        {},
        format="json",
        **executor_csrf,
    )
    assert restored.status_code == 200
    assert restored.data["status"] == "draft"
    project.refresh_from_db()
    assert project.status_before_archive is None
    assert project.archived_at is None

    Project.objects.filter(pk=project.pk).update(status="active")
    completed = executor_client.post(
        f"/api/v1/projects/{project.pk}/complete/",
        {},
        format="json",
        **executor_csrf,
    )
    assert completed.status_code == 200
    assert completed.data["status"] == "completed"
    completed_at = completed.data["completed_at"]
    assert completed_at is not None

    reopened = executor_client.post(
        f"/api/v1/projects/{project.pk}/reopen/",
        {},
        format="json",
        **executor_csrf,
    )
    assert reopened.status_code == 200
    assert reopened.data["status"] == "active"
    assert reopened.data["completed_at"] == completed_at

    archived_active = executor_client.post(
        f"/api/v1/projects/{project.pk}/archive/",
        {},
        format="json",
        **executor_csrf,
    )
    assert archived_active.status_code == 200
    project.refresh_from_db()
    assert project.status_before_archive == "active"
    restored_active = executor_client.post(
        f"/api/v1/projects/{project.pk}/restore/",
        {},
        format="json",
        **executor_csrf,
    )
    assert restored_active.status_code == 200
    assert restored_active.data["status"] == "active"
    assert restored_active.data["completed_at"] == completed_at

    completed_again = executor_client.post(
        f"/api/v1/projects/{project.pk}/complete/",
        {},
        format="json",
        **executor_csrf,
    )
    assert completed_again.status_code == 200
    archived_completed = executor_client.post(
        f"/api/v1/projects/{project.pk}/archive/",
        {},
        format="json",
        **executor_csrf,
    )
    assert archived_completed.status_code == 200
    restored_completed = executor_client.post(
        f"/api/v1/projects/{project.pk}/restore/",
        {},
        format="json",
        **executor_csrf,
    )
    assert restored_completed.status_code == 200
    assert restored_completed.data["status"] == "completed"
    assert (
        restored_completed.data["completed_at"] == completed_again.data["completed_at"]
    )
    assert ProjectAuditLog.objects.filter(project=project).count() == 10
