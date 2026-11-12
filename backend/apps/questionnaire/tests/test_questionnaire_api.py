import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


def _active_project(*, project_type="website", goal="Executor goal"):
    from apps.projects.models import ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    executor = get_user_model().objects.create_user(
        email=f"api-executor-{project_type}@example.com"
    )
    customer = get_user_model().objects.create_user(
        email=f"api-customer-{project_type}@example.com"
    )
    outsider = get_user_model().objects.create_user(
        email=f"api-outsider-{project_type}@example.com"
    )
    project = create_project(
        actor=executor,
        data={"name": "Questionnaire project", "project_type": project_type},
    )
    project.status = "active"
    project.save(update_fields=["status", "updated_at"])
    ProjectMember.objects.create(project=project, user=customer, role="customer")
    ProjectPassport.objects.filter(project=project).update(goal=goal)
    return project, executor, customer, outsider


def _auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_customer_reads_schema_starts_and_resumes_a_draft():
    project, _, customer, _ = _active_project()
    client = _auth_client(customer)
    path = f"/api/v1/projects/{project.pk}/questionnaire/"

    initial = client.get(path)
    assert initial.status_code == 200
    assert initial.data["schema"]["project_type"] == "website"
    assert initial.data["schema"]["version"] == 1
    assert initial.data["submission"] is None

    started = client.post(f"{path}submissions/", {}, format="json")
    assert started.status_code == 201
    submission_id = started.data["id"]
    goal = next(
        answer for answer in started.data["answers"] if answer["question_key"] == "goal"
    )
    assert goal["value"] == "Executor goal"
    assert goal["origin"] == "prefilled"
    assert goal["is_confirmed"] is False

    saved = client.patch(
        f"/api/v1/questionnaire/submissions/{submission_id}/answers/",
        {"answers": {"goal": "Customer's revised goal", "has_integrations": False}},
        format="json",
    )
    assert saved.status_code == 200
    answers = {answer["question_key"]: answer for answer in saved.data["answers"]}
    assert answers["goal"]["value"] == "Customer's revised goal"
    assert answers["goal"]["origin"] == "customer"
    assert answers["integrations"]["value"] == []

    resumed = client.get(path)
    assert resumed.status_code == 200
    assert resumed.data["submission"]["id"] == submission_id
    assert resumed.data["submission"]["answers"] == saved.data["answers"]


@pytest.mark.django_db
def test_schema_api_selects_each_project_type_and_exposes_the_full_branch_contract():
    for project_type, expected_question in (
        ("website", "existing_site_url"),
        ("telegram_bot", "existing_bot_url"),
        ("automation", "schedule_details"),
        ("other", "project_area"),
    ):
        project, _, customer, _ = _active_project(project_type=project_type)
        response = _auth_client(customer).get(
            f"/api/v1/projects/{project.pk}/questionnaire/"
        )

        assert response.status_code == 200
        assert response.data["schema"]["project_type"] == project_type
        assert expected_question in {
            question["key"] for question in response.data["schema"]["questions"]
        }


@pytest.mark.django_db
def test_draft_api_rejects_unknown_and_inactive_branch_answers_without_mutation():
    from apps.questionnaire.models import QuestionnaireAnswer

    project, _, customer, _ = _active_project()
    client = _auth_client(customer)
    start = client.post(
        f"/api/v1/projects/{project.pk}/questionnaire/submissions/",
        {},
        format="json",
    )
    submission_id = start.data["id"]

    invalid = client.patch(
        f"/api/v1/questionnaire/submissions/{submission_id}/answers/",
        {
            "answers": {
                "has_existing_site": False,
                "existing_site_url": "https://old.example.com",
            }
        },
        format="json",
    )
    unknown = client.patch(
        f"/api/v1/questionnaire/submissions/{submission_id}/answers/",
        {"answers": {"executor_only_field": "not accepted"}},
        format="json",
    )

    assert invalid.status_code == 400
    assert "existing_site_url" in invalid.data["errors"]
    assert unknown.status_code == 400
    assert QuestionnaireAnswer.objects.filter(submission_id=submission_id).count() == 1


@pytest.mark.django_db
def test_questionnaire_api_enforces_customer_membership_and_project_scope():
    project, executor, customer, outsider = _active_project()
    second_project, _, second_customer, _ = _active_project(project_type="other")
    executor_client = _auth_client(executor)
    customer_client = _auth_client(customer)
    outsider_client = _auth_client(outsider)

    assert (
        executor_client.get(f"/api/v1/projects/{project.pk}/questionnaire/").status_code
        == 200
    )
    assert (
        executor_client.post(
            f"/api/v1/projects/{project.pk}/questionnaire/submissions/",
            {},
            format="json",
        ).status_code
        == 403
    )
    assert (
        outsider_client.get(f"/api/v1/projects/{project.pk}/questionnaire/").status_code
        == 404
    )

    started = customer_client.post(
        f"/api/v1/projects/{project.pk}/questionnaire/submissions/",
        {},
        format="json",
    )
    cross_project = _auth_client(second_customer).patch(
        f"/api/v1/questionnaire/submissions/{started.data['id']}/answers/",
        {"answers": {"goal": "Cross project write"}},
        format="json",
    )
    assert cross_project.status_code == 404


@pytest.mark.django_db
def test_questionnaire_draft_mutations_require_active_project():
    from apps.projects.models import Project

    project, _, customer, _ = _active_project()
    Project.objects.filter(pk=project.pk).update(status="completed")

    response = _auth_client(customer).post(
        f"/api/v1/projects/{project.pk}/questionnaire/submissions/",
        {},
        format="json",
    )

    assert response.status_code == 409
    assert response.data["code"] == "conflict"
