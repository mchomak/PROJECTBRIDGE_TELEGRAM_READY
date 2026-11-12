from copy import deepcopy
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.common.services import record_project_action
from apps.projects.models import ProjectMemberRole, ProjectStatus
from apps.projects.selectors import (
    get_active_project_members,
    get_passport_for_member,
    get_project_for_member,
)
from apps.projects.services import (
    ProjectNotFoundError,
    ProjectPassportVersionConflictError,
    ProjectPermissionError,
    ProjectStateConflictError,
    apply_questionnaire_mapping,
    lock_passport_for_update,
    update_passport,
)

from .models import (
    QuestionnaireAnswer,
    QuestionnaireAnswerOrigin,
    QuestionnaireConflict,
    QuestionnaireConflictDecision,
    QuestionnaireConflictStatus,
    QuestionnaireSubmission,
    QuestionnaireSubmissionStatus,
)
from .schemas.registry import (
    QuestionnaireSchemaError,
    get_passport_prefill,
    get_schema,
    validate_answers,
)
from .selectors import get_draft_for_project, get_submissions_for_project


class QuestionnaireNotFoundError(Exception):
    """The actor cannot access the requested project questionnaire."""


class QuestionnairePermissionError(Exception):
    """The actor is not the active customer for this project."""


class QuestionnaireStateConflictError(Exception):
    """The project or draft state does not allow this questionnaire action."""


class QuestionnairePassportVersionConflictError(Exception):
    """The passport changed after the customer began this questionnaire draft."""


class QuestionnaireConfirmationRequiredError(Exception):
    """The customer must explicitly confirm values prefilled from the passport."""


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
    """Read the versioned questionnaire, active version, and immutable history."""
    project, _ = _project_and_role(project_id=project_id, actor=actor)
    history = list(get_submissions_for_project(project_id=project.pk))
    submission = get_draft_for_project(project_id=project.pk)
    if submission is None:
        submission = history[0] if history else None
    if submission is None:
        schema = get_schema(project.project_type)
    else:
        schema = get_schema(submission.schema_key, submission.schema_version)
    return {
        "project": project,
        "schema": schema,
        "submission": submission,
        "history": history,
    }


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
                passport_version=passport.version,
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


def refresh_submission_passport_version(*, submission_id, actor):
    """Refresh a stale draft's concurrency token without changing its answers."""
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

        passport = get_passport_for_member(project_id=project.pk, user=actor)
        if passport is None:
            raise QuestionnaireNotFoundError

        submission.passport_version = passport.version
        submission.save(update_fields=("passport_version",))
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


def _is_empty_answer(value):
    return value is None or value == "" or value == [] or value == {}


def _passport_path_value(passport, mapped_field):
    parts = mapped_field.split(".")
    value = getattr(passport, parts[0])
    for part in parts[1:]:
        if not isinstance(value, dict):
            return value
        value = value.get(part)
    return value


def _set_path_change(passport, changes, mapped_field, value):
    parts = mapped_field.split(".")
    root_field = parts[0]
    if len(parts) == 1:
        changes[root_field] = value
        return

    root = deepcopy(changes.get(root_field, getattr(passport, root_field)))
    if not isinstance(root, dict):
        root = {}
    current = root
    for part in parts[1:-1]:
        nested = current.get(part)
        if not isinstance(nested, dict):
            nested = {}
            current[part] = nested
        current = nested
    current[parts[-1]] = value
    changes[root_field] = root


def _passport_value_for_mapping(mapped_field, answer_value):
    root_field = mapped_field.split(".", 1)[0]
    if root_field == "deadline" and answer_value:
        return date.fromisoformat(answer_value)
    if root_field in {"budget_min", "budget_max"} and answer_value not in (None, ""):
        return Decimal(str(answer_value))
    return answer_value


def _snapshot_value(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    if isinstance(value, dict):
        return {key: _snapshot_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_snapshot_value(item) for item in value]
    return value


def _mapping_values_equal(mapped_field, passport_value, answer_value):
    root_field = mapped_field.split(".", 1)[0]
    if root_field == "deadline":
        if passport_value is None:
            return answer_value in (None, "")
        return passport_value.isoformat() == answer_value
    if root_field in {"budget_min", "budget_max"}:
        if passport_value is None:
            return answer_value in (None, "")
        return Decimal(str(passport_value)) == Decimal(str(answer_value))
    return passport_value == answer_value


def _submission_mapping_candidates(*, schema, answer_values, answer_rows):
    project_type = schema["project_type"]
    candidates = []
    type_specific_keys = set()
    control_keys = {
        "has_integrations",
        "has_existing_site",
        "has_existing_bot",
    }

    for question in schema["questions"]:
        key = question["key"]
        mapping = question.get("mapping")
        if mapping is None:
            if key not in control_keys:
                type_specific_keys.add(key)
            continue
        if key not in answer_values:
            continue

        value = answer_values[key]
        if mapping == "integrations":
            enabled = answer_values.get("has_integrations") is True
            value = {
                "enabled": enabled,
                "items": answer_values.get("integrations", []) if enabled else [],
            }
            source = answer_rows.get("integrations") or answer_rows.get(
                "has_integrations"
            )
            mapped_field = f"integrations.{project_type}"
        elif mapping in {"functional_scope", "constraints"}:
            if _is_empty_answer(value):
                continue
            source = answer_rows[key]
            mapped_field = f"{mapping}.{project_type}"
        else:
            if _is_empty_answer(value):
                continue
            source = answer_rows[key]
            mapped_field = mapping

        if source is not None:
            candidates.append((source, mapped_field, value))

    for key in sorted(type_specific_keys):
        if key not in answer_values or _is_empty_answer(answer_values[key]):
            continue
        candidates.append(
            (
                answer_rows[key],
                f"additional_data.questionnaire.{project_type}.answers.{key}",
                answer_values[key],
            )
        )
    return candidates


def _questionnaire_additional_version_path(*, schema):
    return f"additional_data.questionnaire.{schema['project_type']}.schema_version"


def submit_submission(*, submission_id, actor, confirm_prefilled=False):
    """Validate, map and lock a customer submission in one transaction."""
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
        answer_rows = {
            answer.question_key: answer
            for answer in submission.answers.select_for_update().all()
        }
        answer_values = {key: answer.value for key, answer in answer_rows.items()}
        normalized = validate_answers(schema, answer_values, require_complete=True)
        unconfirmed_prefills = [
            answer
            for answer in answer_rows.values()
            if answer.origin == QuestionnaireAnswerOrigin.PREFILLED
            and not answer.is_confirmed
        ]
        if unconfirmed_prefills and not confirm_prefilled:
            raise QuestionnaireConfirmationRequiredError

        passport = get_passport_for_member(project_id=project.pk, user=actor)
        if passport is None:
            raise QuestionnaireNotFoundError

        candidates = _submission_mapping_candidates(
            schema=schema,
            answer_values=normalized,
            answer_rows=answer_rows,
        )
        mapped_changes = {}
        conflicts = []
        for source_answer, mapped_field, answer_value in candidates:
            current_value = _passport_path_value(passport, mapped_field)
            passport_empty = _is_empty_answer(current_value)
            if passport_empty:
                _set_path_change(
                    passport,
                    mapped_changes,
                    mapped_field,
                    _passport_value_for_mapping(mapped_field, answer_value),
                )
            elif _mapping_values_equal(mapped_field, current_value, answer_value):
                continue
            else:
                conflicts.append(
                    {
                        "answer": source_answer,
                        "mapped_field": mapped_field,
                        "passport_value": _snapshot_value(current_value),
                        "answer_value": _snapshot_value(answer_value),
                    }
                )

        version_path = _questionnaire_additional_version_path(schema=schema)
        current_schema_version = _passport_path_value(passport, version_path)
        if current_schema_version != schema["version"]:
            _set_path_change(
                passport,
                mapped_changes,
                version_path,
                schema["version"],
            )

        try:
            updated_passport = apply_questionnaire_mapping(
                project_id=project.pk,
                actor=actor,
                expected_version=submission.passport_version,
                mapped_changes=mapped_changes,
            )
        except ProjectPassportVersionConflictError as exc:
            raise QuestionnairePassportVersionConflictError from exc
        except ProjectNotFoundError as exc:
            raise QuestionnaireNotFoundError from exc
        except ProjectPermissionError as exc:
            raise QuestionnairePermissionError from exc
        except ProjectStateConflictError as exc:
            raise QuestionnaireStateConflictError from exc
        QuestionnaireConflict.objects.bulk_create(
            [
                QuestionnaireConflict(
                    submission=submission,
                    answer=conflict["answer"],
                    mapped_field=conflict["mapped_field"],
                    passport_value=conflict["passport_value"],
                    answer_value=conflict["answer_value"],
                )
                for conflict in conflicts
            ]
        )

        submission.status = QuestionnaireSubmissionStatus.SUBMITTED
        submission.submitted_by = actor
        submission.submitted_at = timezone.now()
        submission.save(update_fields=("status", "submitted_by", "submitted_at"))
        QuestionnaireAnswer.objects.filter(submission=submission).update(
            is_confirmed=True,
            updated_at=timezone.now(),
        )
        applied_fields = sorted(mapped_changes)
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action="questionnaire.submitted",
            target_type="questionnaire_submission",
            target_id=submission.pk,
            metadata={
                "changed_fields": applied_fields,
                "previous_version": submission.passport_version,
                "version": updated_passport.version,
            },
        )
        return submission


def request_correction(*, submission_id, actor):
    """Create one correction draft while retaining the submitted history."""
    with transaction.atomic():
        source = (
            QuestionnaireSubmission.objects.select_for_update()
            .select_related("project")
            .prefetch_related("answers")
            .filter(pk=submission_id)
            .first()
        )
        if source is None:
            raise QuestionnaireNotFoundError
        project, role = _project_and_role(project_id=source.project_id, actor=actor)
        if role != ProjectMemberRole.EXECUTOR:
            raise QuestionnairePermissionError
        if project.status != ProjectStatus.ACTIVE:
            raise QuestionnaireStateConflictError

        existing_correction = QuestionnaireSubmission.objects.filter(
            supersedes=source,
            status=QuestionnaireSubmissionStatus.DRAFT,
        ).first()
        if source.status == QuestionnaireSubmissionStatus.CORRECTION_REQUESTED:
            if existing_correction is not None:
                return existing_correction
            raise QuestionnaireStateConflictError
        if source.status != QuestionnaireSubmissionStatus.SUBMITTED:
            raise QuestionnaireStateConflictError
        existing_draft = get_draft_for_project(project_id=project.pk)
        if existing_draft is not None:
            if existing_draft.supersedes_id == source.pk:
                return existing_draft
            raise QuestionnaireStateConflictError

        passport = get_passport_for_member(project_id=project.pk, user=actor)
        if passport is None:
            raise QuestionnaireNotFoundError
        correction = QuestionnaireSubmission.objects.create(
            project=project,
            schema_key=source.schema_key,
            schema_version=source.schema_version,
            passport_version=passport.version,
            status=QuestionnaireSubmissionStatus.DRAFT,
            started_by=source.started_by,
            supersedes=source,
        )
        QuestionnaireAnswer.objects.bulk_create(
            [
                QuestionnaireAnswer(
                    submission=correction,
                    question_key=answer.question_key,
                    value=answer.value,
                    origin=answer.origin,
                    is_confirmed=answer.is_confirmed,
                    updated_by=answer.updated_by,
                )
                for answer in source.answers.all()
            ]
        )
        source.status = QuestionnaireSubmissionStatus.CORRECTION_REQUESTED
        source.save(update_fields=("status",))
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action="questionnaire.correction_requested",
            target_type="questionnaire_submission",
            target_id=source.pk,
            metadata={},
        )
        return correction


def get_questionnaire_conflicts_for_project(*, project_id, actor):
    """Return pending questionnaire conflicts to the active executor only."""
    project, role = _project_and_role(project_id=project_id, actor=actor)
    if role != ProjectMemberRole.EXECUTOR:
        raise QuestionnairePermissionError
    return QuestionnaireConflict.objects.filter(
        submission__project_id=project.pk,
        status=QuestionnaireConflictStatus.PENDING,
    ).select_related("submission", "answer")


def resolve_conflict(*, conflict_id, actor, decision, expected_passport_version):
    """Resolve one pending conflict as the executor using the stored snapshots."""
    if decision not in QuestionnaireConflictDecision.values:
        raise QuestionnaireSchemaError(
            "Choose an available conflict decision.", field="decision"
        )
    if (
        isinstance(expected_passport_version, bool)
        or not isinstance(expected_passport_version, int)
        or expected_passport_version < 1
    ):
        raise QuestionnaireSchemaError(
            "A positive passport version is required.",
            field="expected_passport_version",
        )

    with transaction.atomic():
        conflict = (
            QuestionnaireConflict.objects.select_for_update()
            .select_related("submission__project", "answer")
            .filter(pk=conflict_id)
            .first()
        )
        if conflict is None:
            raise QuestionnaireNotFoundError
        project, role = _project_and_role(
            project_id=conflict.submission.project_id,
            actor=actor,
        )
        if role != ProjectMemberRole.EXECUTOR:
            raise QuestionnairePermissionError
        if project.status != ProjectStatus.ACTIVE:
            raise QuestionnaireStateConflictError
        if conflict.status != QuestionnaireConflictStatus.PENDING:
            raise QuestionnaireStateConflictError

        try:
            passport = lock_passport_for_update(
                project_id=project.pk,
                actor=actor,
                expected_version=expected_passport_version,
            )
        except ProjectPassportVersionConflictError as exc:
            raise QuestionnairePassportVersionConflictError from exc
        except ProjectNotFoundError as exc:
            raise QuestionnaireNotFoundError from exc
        except ProjectPermissionError as exc:
            raise QuestionnairePermissionError from exc
        except ProjectStateConflictError as exc:
            raise QuestionnaireStateConflictError from exc

        if not _mapping_values_equal(
            conflict.mapped_field,
            _passport_path_value(passport, conflict.mapped_field),
            conflict.passport_value,
        ):
            raise QuestionnairePassportVersionConflictError

        if decision == QuestionnaireConflictDecision.APPLY_ANSWER:
            changes = {}
            _set_path_change(
                passport,
                changes,
                conflict.mapped_field,
                _passport_value_for_mapping(
                    conflict.mapped_field,
                    conflict.answer_value,
                ),
            )
            try:
                updated_passport = update_passport(
                    project_id=project.pk,
                    actor=actor,
                    expected_version=expected_passport_version,
                    changes=changes,
                )
            except ProjectPassportVersionConflictError as exc:
                raise QuestionnairePassportVersionConflictError from exc
            except ProjectNotFoundError as exc:
                raise QuestionnaireNotFoundError from exc
            except ProjectPermissionError as exc:
                raise QuestionnairePermissionError from exc
            except ProjectStateConflictError as exc:
                raise QuestionnaireStateConflictError from exc
        else:
            updated_passport = passport

        conflict.status = QuestionnaireConflictStatus.RESOLVED
        conflict.decision = decision
        conflict.reviewed_by = actor
        conflict.resolved_at = timezone.now()
        conflict.save(
            update_fields=("status", "decision", "reviewed_by", "resolved_at")
        )
        action = (
            "questionnaire.conflict_applied"
            if decision == QuestionnaireConflictDecision.APPLY_ANSWER
            else "questionnaire.conflict_kept"
        )
        record_project_action(
            project_id=project.pk,
            actor_id=actor.pk,
            action=action,
            target_type="questionnaire_conflict",
            target_id=conflict.pk,
            metadata={
                "changed_fields": [conflict.mapped_field.split(".", 1)[0]]
                if decision == QuestionnaireConflictDecision.APPLY_ANSWER
                else [],
                "previous_version": expected_passport_version,
                "version": updated_passport.version,
            },
        )
        return conflict
