import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.project_state.models import ProjectStage
from apps.projects.models import Project, ProjectMember
from apps.projects.services import create_project
from apps.questionnaire.models import QuestionnaireAnswer, QuestionnaireSubmission


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def project_context():
    user_model = get_user_model()
    executor = user_model.objects.create_user(email="state-api-executor@example.com")
    customer = user_model.objects.create_user(email="state-api-customer@example.com")
    outsider = user_model.objects.create_user(email="state-api-outsider@example.com")
    project = create_project(
        actor=executor,
        data={"name": "API state project", "project_type": "other"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )
    other_project = create_project(
        actor=outsider,
        data={"name": "Foreign API project", "project_type": "other"},
    )
    return project, executor, customer, outsider, other_project


def _evidence_refs(project, executor):
    submission = QuestionnaireSubmission.objects.create(
        project=project,
        schema_key="other",
        schema_version=1,
        started_by=executor,
        submitted_by=executor,
        status="submitted",
    )
    refs = []
    for key, value in (("goal", "API source one"), ("constraints", "API source two")):
        answer = QuestionnaireAnswer.objects.create(
            submission=submission,
            question_key=key,
            value=value,
            updated_by=executor,
        )
        refs.append(
            {"source_type": "questionnaire_answer", "source_id": str(answer.pk)}
        )
    return refs


@pytest.mark.django_db
def test_members_read_shared_state_but_only_executor_can_create_or_edit(
    project_context,
):
    project, executor, customer, outsider, other_project = project_context
    executor_client = _client(executor)
    customer_client = _client(customer)
    outsider_client = _client(outsider)
    collection_url = f"/api/v1/projects/{project.pk}/stages/"

    created = executor_client.post(
        collection_url,
        {
            "name": "Discovery",
            "description": "Collect requirements",
            "due_date": "2026-12-01",
        },
        format="json",
    )
    customer_list = customer_client.get(collection_url)
    customer_create = customer_client.post(
        collection_url,
        {"name": "Customer edit"},
        format="json",
    )
    outsider_list = outsider_client.get(collection_url)
    cross_project_patch = outsider_client.patch(
        f"/api/v1/stages/{created.data['id']}/",
        {"name": "Cross project edit"},
        format="json",
    )
    other_project_read = outsider_client.get(
        f"/api/v1/projects/{other_project.pk}/stages/"
    )

    assert created.status_code == 201
    assert customer_list.status_code == 200
    assert customer_list.data["results"][0]["name"] == "Discovery"
    assert customer_list.data["results"][0]["due_date"] == "2026-12-01"
    assert customer_create.status_code == 403
    assert outsider_list.status_code == 404
    assert cross_project_patch.status_code == 404
    assert other_project_read.status_code == 200


@pytest.mark.django_db
def test_state_aggregate_has_scoped_collection_links_and_no_progress_percentage(
    project_context,
):
    project, executor, customer, _, _ = project_context
    created = _client(executor).post(
        f"/api/v1/projects/{project.pk}/stages/",
        {"name": "Planning"},
        format="json",
    )
    aggregate = _client(customer).get(f"/api/v1/projects/{project.pk}/state/")

    assert created.status_code == 201
    assert aggregate.status_code == 200
    assert aggregate.data["project_id"] == str(project.pk)
    assert aggregate.data["counts"]["stages"] == 1
    assert aggregate.data["collections"]["stages"].endswith(
        f"/api/v1/projects/{project.pk}/stages/"
    )
    assert not any("percent" in key.lower() for key in aggregate.data)


@pytest.mark.django_db
def test_every_collection_accepts_executor_creation_and_rejects_invalid_status(
    project_context,
):
    project, executor, _, _, _ = project_context
    client = _client(executor)
    cases = [
        ("requirements", {"title": "Signed requirement"}, "requirements"),
        ("tasks", {"title": "Implement API", "due_date": "2026-12-02"}, "tasks"),
        ("open-questions", {"question": "Which provider?"}, "open_questions"),
    ]
    for route, payload, _ in cases:
        response = client.post(
            f"/api/v1/projects/{project.pk}/{route}/",
            payload,
            format="json",
        )
        assert response.status_code == 201

    stage = ProjectStage.objects.create(
        project=project,
        name="Planning",
        created_by=executor,
    )
    invalid_transition = client.patch(
        f"/api/v1/stages/{stage.pk}/",
        {"status": "done"},
        format="json",
    )
    unknown_field = client.post(
        f"/api/v1/projects/{project.pk}/tasks/",
        {"title": "Bad payload", "completion_percentage": 100},
        format="json",
    )

    assert invalid_transition.status_code == 400
    assert unknown_field.status_code == 400


@pytest.mark.django_db
def test_terminal_stage_accepts_content_patch_but_rejects_status_patch(project_context):
    project, executor, _, _, _ = project_context
    client = _client(executor)
    created = client.post(
        f"/api/v1/projects/{project.pk}/stages/",
        {"name": "Completed stage"},
        format="json",
    )
    stage_url = f"/api/v1/stages/{created.data['id']}/"
    activated = client.patch(stage_url, {"status": "active"}, format="json")
    completed = client.patch(stage_url, {"status": "completed"}, format="json")

    content_update = client.patch(
        stage_url,
        {"description": "Final delivery details"},
        format="json",
    )
    attempted_transition = client.patch(
        stage_url,
        {"status": "active"},
        format="json",
    )

    assert created.status_code == 201
    assert activated.status_code == 200
    assert completed.status_code == 200
    assert content_update.status_code == 200
    assert content_update.data["status"] == "completed"
    assert content_update.data["description"] == "Final delivery details"
    assert attempted_transition.status_code == 409


@pytest.mark.django_db
def test_conflict_creation_requires_scoped_evidence_and_resolution_is_audited(
    project_context,
):
    project, executor, customer, outsider, other_project = project_context
    refs = _evidence_refs(project, executor)
    client = _client(executor)
    options = client.get(f"/api/v1/projects/{project.pk}/evidence-options/")
    customer_options = _client(customer).get(
        f"/api/v1/projects/{project.pk}/evidence-options/"
    )
    created = client.post(
        f"/api/v1/projects/{project.pk}/conflicts/",
        {
            "title": "Contradictory goal",
            "description": "Two submitted answers disagree.",
            "evidence_refs": refs,
        },
        format="json",
    )
    too_few = client.post(
        f"/api/v1/projects/{project.pk}/conflicts/",
        {"title": "Insufficient evidence", "evidence_refs": refs[:1]},
        format="json",
    )
    foreign_refs = _evidence_refs(other_project, outsider)
    cross_project = client.post(
        f"/api/v1/projects/{project.pk}/conflicts/",
        {"title": "Foreign evidence", "evidence_refs": foreign_refs},
        format="json",
    )
    resolved = client.patch(
        f"/api/v1/conflicts/{created.data['id']}/",
        {"status": "resolved", "resolution": "Use the reviewed project goal."},
        format="json",
    )
    repeated = client.patch(
        f"/api/v1/conflicts/{created.data['id']}/",
        {"status": "dismissed"},
        format="json",
    )

    assert created.status_code == 201
    assert len(created.data["evidence"]) == 2
    assert options.status_code == 200
    assert options.data["count"] == 2
    assert {item["source_id"] for item in options.data["results"]} == {
        reference["source_id"] for reference in refs
    }
    assert customer_options.status_code == 403
    assert too_few.status_code == 400
    assert cross_project.status_code == 404
    assert resolved.status_code == 200
    assert resolved.data["resolved_by_id"] == str(executor.pk)
    assert resolved.data["resolved_at"] is not None
    assert repeated.status_code == 409


@pytest.mark.django_db
@pytest.mark.parametrize("terminal_status", ["resolved", "dismissed"])
def test_terminal_conflict_rejects_content_patch(project_context, terminal_status):
    project, executor, _, _, _ = project_context
    client = _client(executor)
    created = client.post(
        f"/api/v1/projects/{project.pk}/conflicts/",
        {
            "title": "Conflicting plan",
            "evidence_refs": _evidence_refs(project, executor),
        },
        format="json",
    )
    terminal_changes = {"status": terminal_status}
    if terminal_status == "resolved":
        terminal_changes["resolution"] = "Use the approved scope."
    terminal = client.patch(
        f"/api/v1/conflicts/{created.data['id']}/",
        terminal_changes,
        format="json",
    )
    content_update = client.patch(
        f"/api/v1/conflicts/{created.data['id']}/",
        {"resolution": "Changed after decision."},
        format="json",
    )

    assert created.status_code == 201
    assert terminal.status_code == 200
    assert terminal.data["status"] == terminal_status
    assert content_update.status_code == 409


@pytest.mark.django_db
def test_completed_and_archived_projects_reject_project_state_mutations(
    project_context,
):
    project, executor, _, _, _ = project_context
    client = _client(executor)
    for status_value in ("completed", "archived"):
        Project.objects.filter(pk=project.pk).update(
            status=status_value,
            status_before_archive="draft" if status_value == "archived" else None,
            archived_at="2026-11-12T00:00:00Z" if status_value == "archived" else None,
        )
        response = client.post(
            f"/api/v1/projects/{project.pk}/stages/",
            {"name": f"{status_value} project"},
            format="json",
        )
        assert response.status_code == 409
