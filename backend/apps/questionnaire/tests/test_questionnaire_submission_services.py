from datetime import date

import pytest
from django.utils import timezone


def _active_project(*, project_type="website", passport_changes=None):
    from django.contrib.auth import get_user_model

    from apps.projects.models import ProjectMember, ProjectPassport
    from apps.projects.services import create_project

    User = get_user_model()
    executor = User.objects.create_user(email=f"executor-{project_type}@example.com")
    customer = User.objects.create_user(email=f"customer-{project_type}@example.com")
    customer.email_verified_at = timezone.now()
    customer.save(update_fields=["email_verified_at"])
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


def _complete_answers(project_type):
    answers = {
        "goal": "Launch a customer portal",
        "target_audience": "Existing customers",
        "expected_result": "Customers can self-serve",
        "functional_scope": "Accounts and support requests",
        "has_integrations": True,
        "integrations": ["Billing"],
        "constraints": "Keep the existing login",
        "deadline": "2027-02-01",
        "budget_min": "100",
        "budget_max": "500",
        "currency": "USD",
    }
    if project_type == "website":
        answers.update(
            has_existing_site=True,
            existing_site_url="https://portal.example.com",
        )
    elif project_type == "telegram_bot":
        answers.update(
            has_existing_bot=True,
            existing_bot_url="https://t.me/projectbridge_bot",
        )
    elif project_type == "automation":
        answers.update(trigger_type="event", event_source="New order created")
    else:
        answers["project_area"] = "Customer operations"
    return answers


def _start_complete_draft(project_type="website", passport_changes=None):
    from apps.questionnaire.services import save_answers, start_submission

    project, executor, customer = _active_project(
        project_type=project_type,
        passport_changes=passport_changes,
    )
    submission = start_submission(project_id=project.pk, actor=customer)
    save_answers(
        submission_id=submission.pk,
        actor=customer,
        answers=_complete_answers(project_type),
    )
    return project, executor, customer, submission


@pytest.mark.django_db
@pytest.mark.parametrize(
    "project_type", ["website", "telegram_bot", "automation", "other"]
)
def test_submit_applies_explicit_mappings_and_locks_confirmed_answers(project_type):
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import ProjectPassport
    from apps.questionnaire.models import QuestionnaireAnswer
    from apps.questionnaire.services import submit_submission

    project, _, customer, draft = _start_complete_draft(project_type)

    submitted = submit_submission(submission_id=draft.pk, actor=customer)

    submitted.refresh_from_db()
    passport = ProjectPassport.objects.get(project=project)
    assert submitted.status == "submitted"
    assert submitted.submitted_by_id == customer.pk
    assert submitted.submitted_at is not None
    assert submitted.passport_version == 1
    answers = QuestionnaireAnswer.objects.filter(submission=submitted)
    assert answers.count() == len(_complete_answers(project_type))
    assert not answers.filter(is_confirmed=False).exists()
    assert passport.goal == "Launch a customer portal"
    assert passport.target_audience == "Existing customers"
    assert passport.expected_result == "Customers can self-serve"
    assert passport.functional_scope[project_type] == "Accounts and support requests"
    assert passport.integrations[project_type] == {
        "enabled": True,
        "items": ["Billing"],
    }
    assert passport.constraints[project_type] == "Keep the existing login"
    assert passport.deadline == date(2027, 2, 1)
    assert passport.budget_min == 100
    assert passport.budget_max == 500
    assert passport.currency == "USD"
    assert (
        passport.additional_data["questionnaire"][project_type]["schema_version"] == 1
    )
    type_answers = passport.additional_data["questionnaire"][project_type].get(
        "answers", {}
    )
    expected_type_answers = {
        "website": {
            "existing_site_url": "https://portal.example.com",
        },
        "telegram_bot": {"existing_bot_url": "https://t.me/projectbridge_bot"},
        "automation": {
            "trigger_type": "event",
            "event_source": "New order created",
        },
        "other": {"project_area": "Customer operations"},
    }
    assert type_answers == expected_type_answers[project_type]
    assert "has_integrations" not in type_answers
    assert not {"has_existing_site", "has_existing_bot"} & set(type_answers)
    assert passport.version == 2
    audit = ProjectAuditLog.objects.get(
        project=project,
        action="questionnaire.submitted",
    )
    assert audit.actor_id == customer.pk
    assert audit.target_id == str(submitted.pk)
    assert "Launch a customer portal" not in str(audit.metadata)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "project_type", ["website", "telegram_bot", "automation", "other"]
)
def test_disabled_integrations_branch_maps_to_explicit_empty_state(project_type):
    from apps.projects.models import ProjectPassport
    from apps.questionnaire.services import save_answers, submit_submission

    project, _, customer, draft = _start_complete_draft(project_type)
    save_answers(
        submission_id=draft.pk,
        actor=customer,
        answers={"has_integrations": False, "integrations": []},
    )

    submit_submission(submission_id=draft.pk, actor=customer)

    passport = ProjectPassport.objects.get(project=project)
    assert passport.integrations[project_type] == {"enabled": False, "items": []}


@pytest.mark.django_db
def test_empty_optional_answers_do_not_clear_passport_and_differing_values_conflict():
    from apps.projects.models import ProjectPassport
    from apps.questionnaire.models import QuestionnaireConflict
    from apps.questionnaire.services import submit_submission

    project, _, customer, draft = _start_complete_draft(
        passport_changes={
            "goal": "Existing goal",
            "constraints": {"website": "Existing constraints"},
            "deadline": date(2026, 1, 1),
        }
    )
    from apps.questionnaire.services import save_answers

    save_answers(
        submission_id=draft.pk,
        actor=customer,
        answers={"constraints": "", "deadline": ""},
    )
    save_answers(submission_id=draft.pk, actor=customer, answers={"goal": "New goal"})

    submitted = submit_submission(submission_id=draft.pk, actor=customer)

    passport = ProjectPassport.objects.get(project=project)
    conflict = QuestionnaireConflict.objects.get(
        submission=submitted, mapped_field="goal"
    )
    assert passport.goal == "Existing goal"
    assert passport.constraints["website"] == "Existing constraints"
    assert passport.deadline == date(2026, 1, 1)
    assert conflict.passport_value == "Existing goal"
    assert conflict.answer_value == "New goal"
    assert conflict.status == "pending"


@pytest.mark.django_db
def test_stale_passport_version_rolls_back_submission_and_keeps_editable_draft():
    from apps.projects.models import ProjectPassport
    from apps.projects.services import update_passport
    from apps.questionnaire.models import QuestionnaireAnswer
    from apps.questionnaire.services import (
        QuestionnairePassportVersionConflictError,
        submit_submission,
    )

    project, executor, customer, draft = _start_complete_draft()
    update_passport(
        project_id=project.pk,
        actor=executor,
        expected_version=1,
        changes={"goal": "Edited while customer filled form"},
    )

    with pytest.raises(QuestionnairePassportVersionConflictError):
        submit_submission(submission_id=draft.pk, actor=customer)

    draft.refresh_from_db()
    passport = ProjectPassport.objects.get(project=project)
    assert draft.status == "draft"
    assert draft.submitted_at is None
    assert passport.goal == "Edited while customer filled form"
    assert passport.version == 2
    assert (
        QuestionnaireAnswer.objects.filter(
            submission=draft,
            is_confirmed=True,
        ).count()
        == 0
    )


@pytest.mark.django_db
def test_refreshing_stale_draft_version_preserves_answers_and_allows_retry():
    from apps.projects.models import ProjectPassport
    from apps.projects.services import update_passport
    from apps.questionnaire.models import QuestionnaireAnswer, QuestionnaireConflict
    from apps.questionnaire.services import (
        QuestionnairePassportVersionConflictError,
        refresh_submission_passport_version,
        save_answers,
        submit_submission,
    )

    project, executor, customer, draft = _start_complete_draft()
    update_passport(
        project_id=project.pk,
        actor=executor,
        expected_version=1,
        changes={"goal": "Edited while customer filled form"},
    )

    with pytest.raises(QuestionnairePassportVersionConflictError):
        submit_submission(submission_id=draft.pk, actor=customer)

    save_answers(
        submission_id=draft.pk,
        actor=customer,
        answers={"constraints": "Customer saved after stale response"},
    )
    answers_before_refresh = list(
        QuestionnaireAnswer.objects.filter(submission=draft)
        .order_by("question_key")
        .values_list("question_key", "value", "origin", "is_confirmed")
    )
    passport_before_refresh = ProjectPassport.objects.get(project=project)

    refreshed = refresh_submission_passport_version(
        submission_id=draft.pk,
        actor=customer,
    )

    assert refreshed.status == "draft"
    assert refreshed.passport_version == 2
    assert (
        list(
            QuestionnaireAnswer.objects.filter(submission=draft)
            .order_by("question_key")
            .values_list("question_key", "value", "origin", "is_confirmed")
        )
        == answers_before_refresh
    )
    passport_after_refresh = ProjectPassport.objects.get(project=project)
    assert passport_after_refresh.version == passport_before_refresh.version == 2
    assert passport_after_refresh.goal == "Edited while customer filled form"

    submitted = submit_submission(submission_id=draft.pk, actor=customer)

    assert submitted.status == "submitted"
    assert QuestionnaireConflict.objects.filter(
        submission=submitted, mapped_field="goal", status="pending"
    ).exists()


@pytest.mark.django_db
def test_prefilled_answers_need_explicit_customer_confirmation_before_submit():
    from apps.questionnaire.models import QuestionnaireAnswer
    from apps.questionnaire.services import (
        QuestionnaireConfirmationRequiredError,
        save_answers,
        start_submission,
        submit_submission,
    )

    project, _, customer = _active_project(
        passport_changes={"goal": "Prefilled goal"},
    )
    draft = start_submission(project_id=project.pk, actor=customer)
    answers = _complete_answers("website")
    answers.pop("goal")
    save_answers(submission_id=draft.pk, actor=customer, answers=answers)

    with pytest.raises(QuestionnaireConfirmationRequiredError):
        submit_submission(submission_id=draft.pk, actor=customer)

    submitted = submit_submission(
        submission_id=draft.pk,
        actor=customer,
        confirm_prefilled=True,
    )

    goal = QuestionnaireAnswer.objects.get(submission=submitted, question_key="goal")
    assert goal.value == "Prefilled goal"
    assert goal.origin == "prefilled"
    assert goal.is_confirmed is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("decision", "expected_goal", "expected_version"),
    [
        ("keep_passport", "Existing goal", 2),
        ("apply_answer", "New goal", 3),
    ],
)
def test_executor_resolves_conflict_with_versioned_decision(
    decision, expected_goal, expected_version
):
    from apps.common.models import ProjectAuditLog
    from apps.projects.models import ProjectPassport
    from apps.questionnaire.models import QuestionnaireConflict
    from apps.questionnaire.services import resolve_conflict, submit_submission

    project, executor, customer, draft = _start_complete_draft(
        passport_changes={"goal": "Existing goal"}
    )
    from apps.questionnaire.services import save_answers

    save_answers(submission_id=draft.pk, actor=customer, answers={"goal": "New goal"})
    submitted = submit_submission(submission_id=draft.pk, actor=customer)
    conflict = QuestionnaireConflict.objects.get(
        submission=submitted, mapped_field="goal"
    )

    resolved = resolve_conflict(
        conflict_id=conflict.pk,
        actor=executor,
        decision=decision,
        expected_passport_version=2,
    )

    passport = ProjectPassport.objects.get(project=project)
    assert resolved.status == "resolved"
    assert resolved.decision == decision
    assert resolved.reviewed_by_id == executor.pk
    assert resolved.resolved_at is not None
    assert passport.goal == expected_goal
    assert passport.version == expected_version
    audit_action = (
        "questionnaire.conflict_kept"
        if decision == "keep_passport"
        else "questionnaire.conflict_applied"
    )
    audit = ProjectAuditLog.objects.get(
        project=project,
        action=audit_action,
        target_id=str(conflict.pk),
    )
    assert audit.actor_id == executor.pk
    assert "New goal" not in str(audit.metadata)


@pytest.mark.django_db
def test_keep_conflict_rechecks_the_locked_current_passport_snapshot(monkeypatch):
    from copy import copy

    from apps.projects.models import ProjectPassport
    from apps.projects.services import update_passport
    from apps.questionnaire.models import QuestionnaireConflict
    from apps.questionnaire.services import (
        QuestionnairePassportVersionConflictError,
        resolve_conflict,
        save_answers,
        submit_submission,
    )

    project, executor, customer, draft = _start_complete_draft(
        passport_changes={"goal": "Existing goal"}
    )
    save_answers(submission_id=draft.pk, actor=customer, answers={"goal": "New goal"})
    submitted = submit_submission(submission_id=draft.pk, actor=customer)
    conflict = QuestionnaireConflict.objects.get(
        submission=submitted, mapped_field="goal"
    )
    stale_snapshot = copy(ProjectPassport.objects.get(project=project))
    update_passport(
        project_id=project.pk,
        actor=executor,
        expected_version=2,
        changes={"goal": "Updated while conflict was pending"},
    )
    monkeypatch.setattr(
        "apps.questionnaire.services.get_passport_for_member",
        lambda *, project_id, user: stale_snapshot,
    )

    with pytest.raises(QuestionnairePassportVersionConflictError):
        resolve_conflict(
            conflict_id=conflict.pk,
            actor=executor,
            decision="keep_passport",
            expected_passport_version=2,
        )

    conflict.refresh_from_db()
    passport = ProjectPassport.objects.get(project=project)
    assert conflict.status == "pending"
    assert passport.goal == "Updated while conflict was pending"
    assert passport.version == 3


@pytest.mark.django_db
def test_correction_creates_idempotent_superseding_draft_without_mutating_history():
    from apps.questionnaire.models import QuestionnaireAnswer
    from apps.questionnaire.services import request_correction, submit_submission

    project, executor, customer, draft = _start_complete_draft()
    submitted = submit_submission(submission_id=draft.pk, actor=customer)
    original_answers = list(
        QuestionnaireAnswer.objects.filter(submission=submitted)
        .order_by("question_key")
        .values_list("question_key", "value", "origin", "is_confirmed")
    )

    correction = request_correction(submission_id=submitted.pk, actor=executor)
    repeated = request_correction(submission_id=submitted.pk, actor=executor)

    submitted.refresh_from_db()
    copied_answers = list(
        QuestionnaireAnswer.objects.filter(submission=correction)
        .order_by("question_key")
        .values_list("question_key", "value", "origin", "is_confirmed")
    )
    assert submitted.status == "correction_requested"
    assert correction.pk == repeated.pk
    assert correction.status == "draft"
    assert correction.supersedes_id == submitted.pk
    assert correction.schema_key == submitted.schema_key
    assert correction.schema_version == submitted.schema_version
    assert correction.passport_version == 2
    assert copied_answers == original_answers
    assert (
        list(
            QuestionnaireAnswer.objects.filter(submission=submitted)
            .order_by("question_key")
            .values_list("question_key", "value", "origin", "is_confirmed")
        )
        == original_answers
    )


@pytest.mark.django_db
def test_customer_cannot_submit_other_customers_draft_or_request_correction():
    from django.contrib.auth import get_user_model

    from apps.projects.models import ProjectMember
    from apps.questionnaire.services import (
        QuestionnaireNotFoundError,
        QuestionnairePermissionError,
        request_correction,
        submit_submission,
    )

    project, executor, customer, draft = _start_complete_draft()
    other_customer = get_user_model().objects.create_user(email="other@example.com")
    other_customer.email_verified_at = timezone.now()
    other_customer.save(update_fields=["email_verified_at"])
    ProjectMember.objects.create(
        project=project,
        user=other_customer,
        role="customer",
        status="left",
    )

    with pytest.raises(QuestionnaireNotFoundError):
        submit_submission(submission_id=draft.pk, actor=other_customer)
    with pytest.raises(QuestionnairePermissionError):
        request_correction(submission_id=draft.pk, actor=customer)
    with pytest.raises(QuestionnairePermissionError):
        submit_submission(submission_id=draft.pk, actor=executor)
