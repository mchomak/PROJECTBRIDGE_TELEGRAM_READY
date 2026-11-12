from django.db import IntegrityError, transaction

from apps.projects.models import ProjectStatus
from apps.projects.selectors import (
    get_active_project_members,
    get_passport_for_member,
    get_project_for_member,
)

from .models import (
    QuestionnaireAnswer,
    QuestionnaireAnswerOrigin,
    QuestionnaireSubmission,
    QuestionnaireSubmissionStatus,
)
from .schemas.registry import (
    QuestionnaireSchemaError,
    get_passport_prefill,
    get_schema,
    validate_answers,
)
from .selectors import get_draft_for_project


class QuestionnaireNotFoundError(Exception):
    """The actor cannot access the requested project questionnaire."""


class QuestionnairePermissionError(Exception):
    """The actor is not the active customer for this project."""


class QuestionnaireStateConflictError(Exception):
    """The project or draft state does not allow this questionnaire action."""


def _project_and_role(*, project_id, actor):
    project = get_project_for_member(project_id=project_id, user=actor)
    if project is None:
        raise QuestionnaireNotFoundError

    member = next(
        (
            candidate
            for candidate in get_active_project_members(project_id=project.pk)
            if candidate.user_id == actor.pk
        ),
        None,
    )
    if member is None:
        raise QuestionnaireNotFoundError
    return project, member.role


def _require_customer(*, role):
    if role != "customer":
        raise QuestionnairePermissionError


def get_questionnaire_for_project(*, project_id, actor):
    """Read the versioned project questionnaire and its current draft."""
    project, _ = _project_and_role(project_id=project_id, actor=actor)
    submission = get_draft_for_project(project_id=project.pk)
    if submission is None:
        schema = get_schema(project.project_type)
    else:
        schema = get_schema(submission.schema_key, submission.schema_version)
    return {"project": project, "schema": schema, "submission": submission}


def start_submission(*, project_id, actor):
    """Create or resume the one editable draft for an active customer project."""
    project, role = _project_and_role(project_id=project_id, actor=actor)
    _require_customer(role=role)
    if project.status != ProjectStatus.ACTIVE:
        raise QuestionnaireStateConflictError

    existing = get_draft_for_project(project_id=project.pk)
    if existing is not None:
        return existing

    schema = get_schema(project.project_type)
    passport = get_passport_for_member(project_id=project.pk, user=actor)
    prefills = get_passport_prefill(schema, passport)
    try:
        with transaction.atomic():
            submission = QuestionnaireSubmission.objects.create(
                project=project,
                schema_key=schema["schema_key"],
                schema_version=schema["version"],
                status=QuestionnaireSubmissionStatus.DRAFT,
                started_by=actor,
            )
            QuestionnaireAnswer.objects.bulk_create(
                [
                    QuestionnaireAnswer(
                        submission=submission,
                        question_key=key,
                        value=value,
                        origin=QuestionnaireAnswerOrigin.PREFILLED,
                        is_confirmed=False,
                        updated_by=actor,
                    )
                    for key, value in prefills.items()
                ]
            )
    except IntegrityError:
        # A simultaneous start is resolved by the partial unique draft constraint.
        existing = get_draft_for_project(project_id=project.pk)
        if existing is not None:
            return existing
        raise
    return submission


def _merge_active_answers(*, schema, current, incoming):
    if not isinstance(incoming, dict):
        raise QuestionnaireSchemaError("Answers must be an object.")

    merged = {**current, **incoming}
    questions = {question["key"]: question for question in schema["questions"]}
    unknown = set(incoming) - set(questions)
    if unknown:
        key = sorted(unknown)[0]
        raise QuestionnaireSchemaError(
            "This question is not part of the schema.", field=key
        )

    for key, question in questions.items():
        condition = question.get("visible_if")
        if (
            condition is None
            or merged.get(condition["question"]) == condition["equals"]
        ):
            continue
        if key in incoming:
            if (
                key == "integrations"
                and merged.get("has_integrations") is False
                and incoming[key] == []
            ):
                continue
            raise QuestionnaireSchemaError(
                "This answer belongs to an inactive branch.", field=key
            )
        merged.pop(key, None)
    return validate_answers(schema, merged)


def save_answers(*, submission_id, actor, answers):
    """Validate and replace draft answers without mutating the passport."""
    with transaction.atomic():
        submission = (
            QuestionnaireSubmission.objects.select_for_update()
            .select_related("project")
            .filter(pk=submission_id)
            .first()
        )
        if submission is None:
            raise QuestionnaireNotFoundError

        project, role = _project_and_role(project_id=submission.project_id, actor=actor)
        _require_customer(role=role)
        if submission.started_by_id != actor.pk:
            raise QuestionnaireNotFoundError
        if project.status != ProjectStatus.ACTIVE:
            raise QuestionnaireStateConflictError
        if submission.status != QuestionnaireSubmissionStatus.DRAFT:
            raise QuestionnaireStateConflictError

        schema = get_schema(submission.schema_key, submission.schema_version)
        existing = {answer.question_key: answer for answer in submission.answers.all()}
        current = {key: answer.value for key, answer in existing.items()}
        normalized = _merge_active_answers(
            schema=schema, current=current, incoming=answers
        )

        removed = set(existing) - set(normalized)
        if removed:
            submission.answers.filter(question_key__in=removed).delete()

        for key, value in normalized.items():
            previous = existing.get(key)
            changed_by_customer = (
                key in answers or previous is None or previous.value != value
            )
            if changed_by_customer:
                QuestionnaireAnswer.objects.update_or_create(
                    submission=submission,
                    question_key=key,
                    defaults={
                        "value": value,
                        "origin": QuestionnaireAnswerOrigin.CUSTOMER,
                        "is_confirmed": False,
                        "updated_by": actor,
                    },
                )
            elif previous is not None:
                # Existing prefilled answers stay labelled until edited.
                continue
            else:
                QuestionnaireAnswer.objects.create(
                    submission=submission,
                    question_key=key,
                    value=value,
                    origin=QuestionnaireAnswerOrigin.CUSTOMER,
                    is_confirmed=False,
                    updated_by=actor,
                )

        return submission
