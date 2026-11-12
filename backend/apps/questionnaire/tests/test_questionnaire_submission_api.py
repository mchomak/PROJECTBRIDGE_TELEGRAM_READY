import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient


def _project_with_members(*, passport_goal=""):
    from apps.projects.models import ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    executor = get_user_model().objects.create_user(
        email="t04-api-executor@example.com"
    )
    customer = get_user_model().objects.create_user(
        email="t04-api-customer@example.com"
    )
    outsider = get_user_model().objects.create_user(
        email="t04-api-outsider@example.com"
    )
    customer.email_verified_at = timezone.now()
    customer.save(update_fields=["email_verified_at"])
    project = create_project(
        actor=executor,
        data={"name": "T04 questionnaire", "project_type": "website"},
    )
    project.status = "active"
    project.save(update_fields=["status", "updated_at"])
    ProjectMember.objects.create(project=project, user=customer, role="customer")
    if passport_goal:
        ProjectPassport.objects.filter(project=project).update(goal=passport_goal)
    return project, executor, customer, outsider


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _complete_answers(*, include_goal=True):
    answers = {
        "target_audience": "Returning customers",
        "expected_result": "Self-service support",
        "functional_scope": "Accounts and requests",
        "has_integrations": False,
        "integrations": [],
        "constraints": "Keep existing sign-in",
        "deadline": "2027-02-01",
        "has_existing_site": False,
    }
    if include_goal:
        answers["goal"] = "Launch a support portal"
    return answers


def _start_and_save(project, customer, *, include_goal=True):
    client = _client(customer)
    start = client.post(
        f"/api/v1/projects/{project.pk}/questionnaire/submissions/",
        {},
        format="json",
    )
    saved = client.patch(
        f"/api/v1/questionnaire/submissions/{start.data['id']}/answers/",
        {"answers": _complete_answers(include_goal=include_goal)},
        format="json",
    )
    assert start.status_code == 201
    assert saved.status_code == 200
    return client, start.data["id"]


@pytest.mark.django_db
def test_customer_submits_completed_answers_and_cannot_edit_the_immutable_version():
    project, _, customer, _ = _project_with_members()
    client, submission_id = _start_and_save(project, customer)

    submitted = client.post(
        f"/api/v1/questionnaire/submissions/{submission_id}/submit/",
        {},
        format="json",
    )
    edit = client.patch(
        f"/api/v1/questionnaire/submissions/{submission_id}/answers/",
        {"answers": {"goal": "Changed after submission"}},
        format="json",
    )

    assert submitted.status_code == 200
    assert submitted.data["status"] == "submitted"
    assert submitted.data["submitted_by_id"] == str(customer.pk)
    assert submitted.data["submitted_at"] is not None
    assert edit.status_code == 409
    assert edit.data["code"] == "conflict"


@pytest.mark.django_db
def test_stale_submission_returns_conflict_and_keeps_the_draft_editable():
    from apps.projects.models import ProjectPassport
    from apps.projects.services import update_passport
    from apps.questionnaire.models import QuestionnaireAnswer, QuestionnaireSubmission

    project, executor, customer, _ = _project_with_members(
        passport_goal="Prefilled goal"
    )
    client, submission_id = _start_and_save(project, customer, include_goal=False)
    update_passport(
        project_id=project.pk,
        actor=executor,
        expected_version=1,
        changes={"goal": "Changed by executor"},
    )

    response = client.post(
        f"/api/v1/questionnaire/submissions/{submission_id}/submit/",
        {"confirm_prefilled": True},
        format="json",
    )
    draft = QuestionnaireSubmission.objects.get(pk=submission_id)

    assert response.status_code == 409
    assert response.data["code"] == "conflict"
    assert response.data["detail"] == (
        "The project passport changed after this questionnaire draft started."
    )
    assert draft.status == "draft"
    assert draft.submitted_at is None

    saved = client.patch(
        f"/api/v1/questionnaire/submissions/{submission_id}/answers/",
        {"answers": {"constraints": "Saved after stale response"}},
        format="json",
    )
    answers_before_refresh = list(
        QuestionnaireAnswer.objects.filter(submission_id=submission_id)
        .order_by("question_key")
        .values_list("question_key", "value", "origin", "is_confirmed")
    )
    refresh_url = (
        f"/api/v1/questionnaire/submissions/{submission_id}/refresh-passport-version/"
    )
    executor_refresh = _client(executor).post(refresh_url, {}, format="json")
    refresh = client.post(
        refresh_url,
        {},
        format="json",
    )

    assert saved.status_code == 200
    assert executor_refresh.status_code == 403
    assert refresh.status_code == 200
    assert refresh.data["passport_version"] == 2
    refreshed_answers = refresh.data["answers"]
    refreshed_goal = next(
        answer for answer in refreshed_answers if answer["question_key"] == "goal"
    )
    refreshed_constraints = next(
        answer
        for answer in refreshed_answers
        if answer["question_key"] == "constraints"
    )
    assert refreshed_goal["value"] == "Prefilled goal"
    assert refreshed_goal["origin"] == "prefilled"
    assert refreshed_goal["is_confirmed"] is False
    assert refreshed_constraints["value"] == "Saved after stale response"
    assert refreshed_constraints["origin"] == "customer"
    assert (
        list(
            QuestionnaireAnswer.objects.filter(submission_id=submission_id)
            .order_by("question_key")
            .values_list("question_key", "value", "origin", "is_confirmed")
        )
        == answers_before_refresh
    )
    unchanged_passport = ProjectPassport.objects.get(project=project)
    assert unchanged_passport.version == 2
    assert unchanged_passport.goal == "Changed by executor"

    retry = client.post(
        f"/api/v1/questionnaire/submissions/{submission_id}/submit/",
        {"confirm_prefilled": True},
        format="json",
    )

    assert retry.status_code == 200
    assert retry.data["status"] == "submitted"


@pytest.mark.django_db
def test_prefilled_values_require_explicit_confirmation_at_submission():
    project, _, customer, _ = _project_with_members(passport_goal="Existing goal")
    client, submission_id = _start_and_save(project, customer, include_goal=False)

    rejected = client.post(
        f"/api/v1/questionnaire/submissions/{submission_id}/submit/",
        {},
        format="json",
    )
    confirmed = client.post(
        f"/api/v1/questionnaire/submissions/{submission_id}/submit/",
        {"confirm_prefilled": True},
        format="json",
    )

    assert rejected.status_code == 400
    assert "confirm_prefilled" in rejected.data["errors"]
    assert confirmed.status_code == 200
    assert confirmed.data["status"] == "submitted"


@pytest.mark.django_db
def test_conflict_queue_and_apply_decision_are_executor_only_and_audited():
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import ProjectPassport

    project, executor, customer, outsider = _project_with_members(
        passport_goal="Executor goal"
    )
    client, submission_id = _start_and_save(project, customer)
    submitted = client.post(
        f"/api/v1/questionnaire/submissions/{submission_id}/submit/",
        {},
        format="json",
    )
    queue_path = f"/api/v1/projects/{project.pk}/questionnaire/conflicts/"
    executor_client = _client(executor)
    customer_queue = client.get(queue_path)
    outsider_queue = _client(outsider).get(queue_path)
    queue = executor_client.get(queue_path)

    assert submitted.status_code == 200
    assert customer_queue.status_code == 403
    assert outsider_queue.status_code == 404
    assert queue.status_code == 200
    conflict = next(item for item in queue.data if item["mapped_field"] == "goal")
    assert conflict["passport_value"] == "Executor goal"
    assert conflict["answer_value"] == "Launch a support portal"
    customer_resolve = client.post(
        f"/api/v1/questionnaire/conflicts/{conflict['id']}/resolve/",
        {"decision": "apply_answer", "expected_passport_version": 2},
        format="json",
    )

    resolved = executor_client.post(
        f"/api/v1/questionnaire/conflicts/{conflict['id']}/resolve/",
        {"decision": "apply_answer", "expected_passport_version": 2},
        format="json",
    )

    assert resolved.status_code == 200
    assert customer_resolve.status_code == 403
    assert resolved.data["decision"] == "apply_answer"
    assert resolved.data["reviewed_by_id"] == str(executor.pk)
    assert (
        ProjectPassport.objects.get(project=project).goal == "Launch a support portal"
    )
    audit = ProjectAuditLog.objects.get(action="questionnaire.conflict_applied")
    assert audit.actor_id == executor.pk
    assert "Launch a support portal" not in str(audit.metadata)


@pytest.mark.django_db
def test_executor_can_request_correction_and_questionnaire_read_preserves_history():
    project, executor, customer, _ = _project_with_members()
    client, submission_id = _start_and_save(project, customer)
    submitted = client.post(
        f"/api/v1/questionnaire/submissions/{submission_id}/submit/",
        {},
        format="json",
    )
    correction_url = (
        f"/api/v1/questionnaire/submissions/{submission_id}/request-correction/"
    )
    customer_attempt = client.post(correction_url, {}, format="json")
    executor_client = _client(executor)
    correction = executor_client.post(correction_url, {}, format="json")
    repeated = executor_client.post(correction_url, {}, format="json")
    read = client.get(f"/api/v1/projects/{project.pk}/questionnaire/")

    assert submitted.status_code == 200
    assert customer_attempt.status_code == 403
    assert correction.status_code == 200
    assert correction.data["status"] == "draft"
    assert correction.data["supersedes_id"] == submission_id
    assert repeated.data["id"] == correction.data["id"]
    assert read.status_code == 200
    assert [item["id"] for item in read.data["history"]] == [
        correction.data["id"],
        submission_id,
    ]
