from datetime import date

import pytest


def _active_project(*, project_type="website", passport_changes=None):
    from django.contrib.auth import get_user_model

    from apps.projects.models import ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    User = get_user_model()
    executor = User.objects.create_user(email=f"executor-{project_type}@example.com")
    customer = User.objects.create_user(email=f"customer-{project_type}@example.com")
    project = create_project(
        actor=executor,
        data={"name": f"{project_type} project", "project_type": project_type},
    )
    project.status = "active"
    project.save(update_fields=["status", "updated_at"])
    ProjectMember.objects.create(project=project, user=customer, role="customer")
    if passport_changes:
        ProjectPassport.objects.filter(project=project).update(**passport_changes)
    return project, executor, customer


@pytest.mark.django_db
@pytest.mark.parametrize(
    "project_type", ["website", "telegram_bot", "automation", "other"]
)
def test_project_questionnaire_uses_the_pinned_type_schema(project_type):
    from apps.questionnaire.services import get_questionnaire_for_project

    project, _, customer = _active_project(project_type=project_type)

    result = get_questionnaire_for_project(project_id=project.pk, actor=customer)

    assert result["schema"]["project_type"] == project_type
    assert result["schema"]["version"] == 1
    assert result["submission"] is None


@pytest.mark.django_db
def test_start_is_idempotent_and_prefills_separate_confirmable_answers():
    from apps.projects.models import ProjectPassport
    from apps.questionnaire.models import QuestionnaireAnswer, QuestionnaireSubmission
    from apps.questionnaire.services import start_submission

    project, _, customer = _active_project(
        project_type="website",
        passport_changes={
            "goal": "Launch a portal",
            "target_audience": "Existing customers",
            "functional_scope": {"website": "Accounts and support requests"},
            "integrations": {"website": {"enabled": True, "items": ["Billing"]}},
            "constraints": {"website": "Keep existing login"},
            "deadline": date(2027, 2, 1),
            "budget_min": "100.0000000000",
            "currency": "USD",
        },
    )

    first = start_submission(project_id=project.pk, actor=customer)
    second = start_submission(project_id=project.pk, actor=customer)

    answers = {
        answer.question_key: answer
        for answer in QuestionnaireAnswer.objects.filter(submission=first)
    }
    assert first.pk == second.pk
    assert QuestionnaireSubmission.objects.filter(project=project).count() == 1
    assert first.schema_key == "website" and first.schema_version == 1
    assert answers["goal"].value == "Launch a portal"
    assert answers["goal"].origin == "prefilled"
    assert answers["goal"].is_confirmed is False
    assert answers["has_integrations"].value is True
    assert answers["integrations"].value == ["Billing"]
    assert answers["deadline"].value == "2027-02-01"
    assert answers["budget_min"].value == "100.0000000000"
    assert "target_audience" in answers
    assert ProjectPassport.objects.get(project=project).goal == "Launch a portal"


@pytest.mark.django_db
def test_saving_draft_marks_customer_origin_and_never_changes_passport():
    from apps.projects.models import ProjectPassport
    from apps.questionnaire.models import QuestionnaireAnswer
    from apps.questionnaire.services import save_answers, start_submission

    project, _, customer = _active_project(
        passport_changes={"goal": "Executor provided goal"}
    )
    submission = start_submission(project_id=project.pk, actor=customer)

    saved = save_answers(
        submission_id=submission.pk,
        actor=customer,
        answers={
            "goal": "Customer confirmed goal",
            "target_audience": "Small businesses",
            "expected_result": "Self-service portal",
            "functional_scope": "Accounts and requests",
            "has_integrations": False,
            "has_existing_site": False,
        },
    )

    goal = QuestionnaireAnswer.objects.get(submission=saved, question_key="goal")
    integrations = QuestionnaireAnswer.objects.get(
        submission=saved,
        question_key="integrations",
    )
    assert saved.status == "draft"
    assert goal.value == "Customer confirmed goal"
    assert goal.origin == "customer"
    assert integrations.value == []
    assert integrations.origin == "customer"
    assert not QuestionnaireAnswer.objects.filter(
        submission=saved,
        question_key="existing_site_url",
    ).exists()
    assert ProjectPassport.objects.get(project=project).goal == "Executor provided goal"


@pytest.mark.django_db
def test_partial_draft_save_preserves_untouched_prefill_origins():
    from apps.questionnaire.models import QuestionnaireAnswer
    from apps.questionnaire.services import save_answers, start_submission

    project, _, customer = _active_project(
        passport_changes={
            "goal": "Passport goal",
            "target_audience": "Existing customers",
            "integrations": {"website": {"enabled": False, "items": []}},
        },
    )
    submission = start_submission(project_id=project.pk, actor=customer)

    saved = save_answers(
        submission_id=submission.pk,
        actor=customer,
        answers={"goal": "Customer changed goal"},
    )

    goal = QuestionnaireAnswer.objects.get(submission=saved, question_key="goal")
    integrations_enabled = QuestionnaireAnswer.objects.get(
        submission=saved,
        question_key="has_integrations",
    )
    target_audience = QuestionnaireAnswer.objects.get(
        submission=saved,
        question_key="target_audience",
    )
    assert goal.origin == "customer"
    assert goal.value == "Customer changed goal"
    assert target_audience.origin == "prefilled"
    assert integrations_enabled.origin == "prefilled"


@pytest.mark.django_db
def test_start_does_not_prefill_unmapped_answers_from_additional_data():
    from apps.questionnaire.models import QuestionnaireAnswer
    from apps.questionnaire.services import start_submission

    project, _, customer = _active_project(
        passport_changes={
            "additional_data": {
                "questionnaire": {
                    "website": {
                        "schema_version": 1,
                        "answers": {
                            "has_existing_site": True,
                            "existing_site_url": "https://legacy.example.com",
                        },
                    }
                }
            }
        },
    )

    submission = start_submission(project_id=project.pk, actor=customer)

    assert not QuestionnaireAnswer.objects.filter(
        submission=submission,
        question_key__in=("has_existing_site", "existing_site_url"),
    ).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("saved_questionnaire", [None, [], "legacy", 42])
def test_start_ignores_malformed_additional_questionnaire_json(saved_questionnaire):
    from apps.questionnaire.services import start_submission

    project, _, customer = _active_project(
        passport_changes={
            "additional_data": {"questionnaire": saved_questionnaire},
        },
    )

    submission = start_submission(project_id=project.pk, actor=customer)

    assert submission.schema_key == "website"


@pytest.mark.django_db
def test_branch_change_removes_old_branch_answer_and_resume_returns_latest_draft():
    from apps.questionnaire.models import QuestionnaireAnswer
    from apps.questionnaire.services import (
        get_questionnaire_for_project,
        save_answers,
        start_submission,
    )

    project, _, customer = _active_project()
    submission = start_submission(project_id=project.pk, actor=customer)
    save_answers(
        submission_id=submission.pk,
        actor=customer,
        answers={
            "has_existing_site": True,
            "existing_site_url": "https://legacy.example.com",
        },
    )

    save_answers(
        submission_id=submission.pk,
        actor=customer,
        answers={"has_existing_site": False},
    )
    resumed = get_questionnaire_for_project(project_id=project.pk, actor=customer)

    assert resumed["submission"].pk == submission.pk
    assert not QuestionnaireAnswer.objects.filter(
        submission=submission,
        question_key="existing_site_url",
    ).exists()


@pytest.mark.django_db
def test_draft_saving_rejects_invalid_branch_and_preserves_existing_values():
    from apps.questionnaire.models import QuestionnaireAnswer
    from apps.questionnaire.schemas.registry import QuestionnaireSchemaError
    from apps.questionnaire.services import save_answers, start_submission

    project, _, customer = _active_project()
    submission = start_submission(project_id=project.pk, actor=customer)
    save_answers(
        submission_id=submission.pk,
        actor=customer,
        answers={"has_existing_site": False},
    )

    with pytest.raises(QuestionnaireSchemaError):
        save_answers(
            submission_id=submission.pk,
            actor=customer,
            answers={"existing_site_url": "https://old.example.com"},
        )

    assert not QuestionnaireAnswer.objects.filter(
        submission=submission,
        question_key="existing_site_url",
    ).exists()


@pytest.mark.django_db
def test_executor_cannot_start_customer_draft_and_foreign_customer_cannot_read_it():
    from apps.questionnaire.services import (
        QuestionnaireNotFoundError,
        QuestionnairePermissionError,
        get_questionnaire_for_project,
        start_submission,
    )

    project, executor, customer = _active_project()
    foreign_project, _, foreign_customer = _active_project(project_type="other")
    submission = start_submission(project_id=project.pk, actor=customer)

    with pytest.raises(QuestionnairePermissionError):
        start_submission(project_id=project.pk, actor=executor)
    with pytest.raises(QuestionnaireNotFoundError):
        get_questionnaire_for_project(project_id=project.pk, actor=foreign_customer)
    with pytest.raises(QuestionnaireNotFoundError):
        from apps.questionnaire.services import save_answers

        save_answers(
            submission_id=submission.pk,
            actor=foreign_customer,
            answers={"goal": "Cross project"},
        )
    assert foreign_project.project_type == "other"
