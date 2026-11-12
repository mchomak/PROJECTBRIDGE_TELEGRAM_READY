from datetime import date
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.chat.services import send_message
from apps.common.models import ProjectAuditLog
from apps.project_state.models import (
    Evidence,
    OpenQuestion,
    ProjectConflict,
    ProjectConflictEvidence,
    ProjectStage,
    Requirement,
    Task,
)
from apps.project_state.services import (
    ProjectStateConflictError,
    ProjectStateNotFoundError,
    ProjectStatePermissionError,
    create_open_question,
    create_project_conflict,
    create_project_stage,
    create_requirement,
    create_task,
    update_open_question,
    update_project_conflict,
    update_project_stage,
    update_requirement,
    update_task,
)
from apps.projects.models import Project, ProjectMember
from apps.projects.services import create_project
from apps.questionnaire.models import QuestionnaireAnswer, QuestionnaireSubmission


@pytest.fixture
def project_context():
    user_model = get_user_model()
    executor = user_model.objects.create_user(email="state-executor@example.com")
    customer = user_model.objects.create_user(email="state-customer@example.com")
    outsider = user_model.objects.create_user(email="state-outsider@example.com")
    project = create_project(
        actor=executor,
        data={"name": "State project", "project_type": "other"},
    )
    ProjectMember.objects.create(
        project=project,
        user=customer,
        role="customer",
        status="active",
    )
    other_project = create_project(
        actor=outsider,
        data={"name": "Other state project", "project_type": "other"},
    )
    return project, executor, customer, outsider, other_project


def _create(entity, *, project_id, actor, **changes):
    data = {
        "project_stage": (create_project_stage, {"name": "Stage"}),
        "requirement": (create_requirement, {"title": "Requirement"}),
        "task": (create_task, {"title": "Task"}),
        "open_question": (create_open_question, {"question": "Question?"}),
    }
    if entity == "project_conflict":
        return create_project_conflict(
            project_id=project_id,
            actor=actor,
            data={"title": "Conflict", **changes},
        )
    service, defaults = data[entity]
    return service(project_id=project_id, actor=actor, data={**defaults, **changes})


def _update_service(entity):
    return {
        "project_stage": update_project_stage,
        "requirement": update_requirement,
        "task": update_task,
        "open_question": update_open_question,
        "project_conflict": update_project_conflict,
    }[entity]


def _evidence_refs(project, actor):
    submission = QuestionnaireSubmission.objects.create(
        project=project,
        schema_key="other",
        schema_version=1,
        started_by=actor,
        status="submitted",
        submitted_by=actor,
    )
    refs = []
    for key, value in (
        ("goal", "First source text"),
        ("constraints", "Second source text"),
    ):
        answer = QuestionnaireAnswer.objects.create(
            submission=submission,
            question_key=key,
            value=value,
            updated_by=actor,
        )
        refs.append({"source_type": "questionnaire_answer", "source_id": answer.pk})
    return refs


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("entity", "target", "path"),
    [
        ("project_stage", "active", ["active"]),
        ("project_stage", "cancelled", ["cancelled"]),
        ("project_stage", "blocked", ["active", "blocked"]),
        ("project_stage", "completed", ["active", "completed"]),
        ("project_stage", "active", ["active", "blocked", "active"]),
        ("project_stage", "cancelled", ["active", "blocked", "cancelled"]),
        ("requirement", "confirmed", ["confirmed"]),
        ("requirement", "rejected", ["rejected"]),
        ("requirement", "rejected", ["confirmed", "rejected"]),
        ("requirement", "in_progress", ["confirmed", "in_progress"]),
        ("requirement", "rejected", ["confirmed", "in_progress", "rejected"]),
        ("requirement", "blocked", ["confirmed", "in_progress", "blocked"]),
        ("requirement", "completed", ["confirmed", "in_progress", "completed"]),
        (
            "requirement",
            "in_progress",
            ["confirmed", "in_progress", "blocked", "in_progress"],
        ),
        (
            "requirement",
            "rejected",
            ["confirmed", "in_progress", "blocked", "rejected"],
        ),
        ("task", "in_progress", ["in_progress"]),
        ("task", "cancelled", ["cancelled"]),
        ("task", "cancelled", ["in_progress", "cancelled"]),
        ("task", "blocked", ["in_progress", "blocked"]),
        ("task", "cancelled", ["in_progress", "blocked", "cancelled"]),
        ("task", "done", ["in_progress", "done"]),
        ("task", "in_progress", ["in_progress", "blocked", "in_progress"]),
        ("open_question", "resolved", ["resolved"]),
        ("open_question", "dismissed", ["dismissed"]),
        ("project_conflict", "resolved", ["resolved"]),
        ("project_conflict", "dismissed", ["dismissed"]),
    ],
)
def test_every_documented_transition_is_service_owned(
    project_context, entity, target, path
):
    project, executor, _, _, _ = project_context
    changes = {"resolution": "Agreed solution"} if entity == "project_conflict" else {}
    evidence = (
        {"evidence_refs": _evidence_refs(project, executor)}
        if entity == "project_conflict"
        else {}
    )
    record = _create(
        entity,
        project_id=project.pk,
        actor=executor,
        **evidence,
    )
    service = _update_service(entity)
    for status_value in path:
        update = {**changes, "status": status_value}
        record = service(record_id=record.pk, actor=executor, changes=update)

    assert record.status == target
    if entity == "requirement" and target == "confirmed":
        assert record.confirmed_by_id == executor.pk
        assert record.confirmed_at is not None
    if entity == "open_question" and target == "resolved":
        assert record.resolved_at is not None
    if entity == "project_conflict" and target in {"resolved", "dismissed"}:
        assert record.resolved_by_id == executor.pk
        assert record.resolved_at is not None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("entity", "terminal", "attempted"),
    [
        ("project_stage", "completed", "active"),
        ("project_stage", "cancelled", "active"),
        ("requirement", "completed", "in_progress"),
        ("requirement", "rejected", "draft"),
        ("task", "done", "in_progress"),
        ("task", "cancelled", "in_progress"),
        ("open_question", "resolved", "open"),
        ("open_question", "dismissed", "open"),
        ("project_conflict", "resolved", "unresolved"),
        ("project_conflict", "dismissed", "unresolved"),
    ],
)
def test_terminal_states_cannot_be_reopened(
    project_context, entity, terminal, attempted
):
    project, executor, _, _, _ = project_context
    evidence = (
        {"evidence_refs": _evidence_refs(project, executor)}
        if entity == "project_conflict"
        else {}
    )
    record = _create(
        entity,
        project_id=project.pk,
        actor=executor,
        **evidence,
    )
    service = _update_service(entity)
    paths = {
        ("project_stage", "completed"): ["active", "completed"],
        ("project_stage", "cancelled"): ["cancelled"],
        ("requirement", "completed"): ["confirmed", "in_progress", "completed"],
        ("requirement", "rejected"): ["rejected"],
        ("task", "done"): ["in_progress", "done"],
        ("task", "cancelled"): ["cancelled"],
        ("open_question", "resolved"): ["resolved"],
        ("open_question", "dismissed"): ["dismissed"],
        ("project_conflict", "resolved"): ["resolved"],
        ("project_conflict", "dismissed"): ["dismissed"],
    }
    for status_value in paths[(entity, terminal)]:
        record = service(
            record_id=record.pk,
            actor=executor,
            changes={
                "status": status_value,
                **(
                    {"resolution": "Final resolution"}
                    if entity == "project_conflict"
                    else {}
                ),
            },
        )

    with pytest.raises(ProjectStateConflictError):
        service(record_id=record.pk, actor=executor, changes={"status": attempted})


@pytest.mark.django_db
def test_terminal_state_allows_content_update_without_status_change(project_context):
    project, executor, _, _, _ = project_context
    stage = create_project_stage(
        project_id=project.pk,
        actor=executor,
        data={"name": "Completed stage"},
    )
    update_project_stage(
        record_id=stage.pk,
        actor=executor,
        changes={"status": "active"},
    )
    completed = update_project_stage(
        record_id=stage.pk,
        actor=executor,
        changes={"status": "completed"},
    )

    updated = update_project_stage(
        record_id=completed.pk,
        actor=executor,
        changes={"description": "Final delivery details"},
    )

    assert updated.status == "completed"
    assert updated.description == "Final delivery details"


@pytest.mark.django_db
@pytest.mark.parametrize("terminal_status", ["resolved", "dismissed"])
def test_terminal_conflict_rejects_content_updates(project_context, terminal_status):
    project, executor, _, _, _ = project_context
    conflict = create_project_conflict(
        project_id=project.pk,
        actor=executor,
        data={
            "title": "Conflicting plan",
            "evidence_refs": _evidence_refs(project, executor),
        },
    )
    changes = {"status": terminal_status}
    if terminal_status == "resolved":
        changes["resolution"] = "Use the approved scope."
    terminal = update_project_conflict(
        record_id=conflict.pk,
        actor=executor,
        changes=changes,
    )

    with pytest.raises(ProjectStateConflictError):
        update_project_conflict(
            record_id=terminal.pk,
            actor=executor,
            changes={"resolution": "Changed after decision."},
        )

    terminal.refresh_from_db()
    assert terminal.status == terminal_status
    assert terminal.resolution == changes.get("resolution", "")


@pytest.mark.django_db
def test_disallowed_transition_between_valid_statuses_is_rejected(project_context):
    project, executor, _, _, _ = project_context
    task = create_task(project_id=project.pk, actor=executor, data={"title": "Build"})

    with pytest.raises(ProjectStateConflictError):
        update_task(record_id=task.pk, actor=executor, changes={"status": "blocked"})


@pytest.mark.django_db
def test_update_audit_records_actor_target_fields_and_transition_without_content(
    project_context,
):
    project, executor, _, _, _ = project_context
    requirement = create_requirement(
        project_id=project.pk,
        actor=executor,
        data={"title": "Original title"},
    )

    updated = update_requirement(
        record_id=requirement.pk,
        actor=executor,
        changes={
            "title": "Sensitive updated title",
            "description": "Sensitive updated description",
            "status": "confirmed",
        },
    )
    audit = ProjectAuditLog.objects.get(
        project=project,
        action="project_state.requirement_updated",
        target_id=str(updated.pk),
    )

    assert audit.actor_id == executor.pk
    assert audit.target_type == "requirement"
    assert audit.metadata == {
        "changed_fields": ["description", "status", "title"],
        "from_status": "draft",
        "to_status": "confirmed",
    }
    assert "Sensitive updated title" not in str(audit.metadata)
    assert "Sensitive updated description" not in str(audit.metadata)


@pytest.mark.django_db
def test_service_rejects_customer_cross_project_and_read_only_project_writes(
    project_context,
):
    project, executor, customer, outsider, other_project = project_context
    stage = create_project_stage(
        project_id=project.pk,
        actor=executor,
        data={"name": "Scoped stage"},
    )

    with pytest.raises(ProjectStatePermissionError):
        create_project_stage(
            project_id=project.pk,
            actor=customer,
            data={"name": "Customer stage"},
        )
    with pytest.raises(ProjectStateNotFoundError):
        update_project_stage(
            record_id=stage.pk,
            actor=outsider,
            changes={"name": "Cross-project edit"},
        )
    Project.objects.filter(pk=project.pk).update(status="completed")
    with pytest.raises(ProjectStateConflictError):
        update_project_stage(
            record_id=stage.pk,
            actor=executor,
            changes={"name": "Completed project edit"},
        )
    with pytest.raises(ProjectStateNotFoundError):
        create_project_stage(
            project_id=other_project.pk,
            actor=executor,
            data={"name": "Unowned project stage"},
        )


@pytest.mark.django_db
def test_task_rejects_stage_or_assignee_from_another_project(project_context):
    project, executor, customer, outsider, other_project = project_context
    foreign_stage = create_project_stage(
        project_id=other_project.pk,
        actor=outsider,
        data={"name": "Foreign stage"},
    )

    with pytest.raises(ValidationError):
        create_task(
            project_id=project.pk,
            actor=executor,
            data={"title": "Bad stage", "stage_id": foreign_stage.pk},
        )
    with pytest.raises(ValidationError):
        create_task(
            project_id=project.pk,
            actor=executor,
            data={"title": "Bad assignee", "assignee_id": outsider.pk},
        )
    task = create_task(
        project_id=project.pk,
        actor=executor,
        data={"title": "Customer assigned", "assignee_id": customer.pk},
    )
    assert task.assignee_id == customer.pk


@pytest.mark.django_db
def test_conflict_snapshots_same_project_questionnaire_answers_and_audits_only_metadata(
    project_context,
):
    project, executor, _, _, _ = project_context
    refs = _evidence_refs(project, executor)
    conflict = create_project_conflict(
        project_id=project.pk,
        actor=executor,
        data={
            "title": "Conflicting scope",
            "description": "Private content should not appear in audit metadata.",
            "evidence_refs": refs,
        },
    )
    evidence = list(conflict.evidence.order_by("excerpt"))

    assert conflict.status == "unresolved"
    assert len(evidence) == 2
    assert {item.source_type for item in evidence} == {"questionnaire_answer"}
    assert {item.excerpt for item in evidence} == {
        '"First source text"',
        '"Second source text"',
    }
    assert all(
        item.metadata["question_key"] in {"goal", "constraints"} for item in evidence
    )
    logs = list(ProjectAuditLog.objects.filter(project=project))
    assert logs
    for log in logs:
        assert "Conflicting scope" not in str(log.metadata)
        assert "Private content" not in str(log.metadata)
        assert "First source text" not in str(log.metadata)
        assert "Second source text" not in str(log.metadata)
        assert set(log.metadata) <= {"changed_fields", "from_status", "to_status"}


@pytest.mark.django_db
def test_conflict_rejects_duplicate_or_cross_project_evidence(project_context):
    project, executor, _, outsider, other_project = project_context
    refs = _evidence_refs(project, executor)
    with pytest.raises(ValidationError):
        create_project_conflict(
            project_id=project.pk,
            actor=executor,
            data={"title": "Too few", "evidence_refs": refs[:1]},
        )
    with pytest.raises(ValidationError):
        create_project_conflict(
            project_id=project.pk,
            actor=executor,
            data={"title": "Duplicate", "evidence_refs": [refs[0], refs[0]]},
        )
    foreign_refs = _evidence_refs(other_project, outsider)
    with pytest.raises(ProjectStateNotFoundError):
        create_project_conflict(
            project_id=project.pk,
            actor=executor,
            data={"title": "Foreign evidence", "evidence_refs": foreign_refs},
        )


@pytest.mark.django_db
def test_message_evidence_snapshots_same_project_source_and_rejects_unknown_or_foreign(
    project_context,
):
    project, executor, _, outsider, other_project = project_context
    Project.objects.filter(pk=project.pk).update(status="active")
    Project.objects.filter(pk=other_project.pk).update(status="active")
    questionnaire_refs = _evidence_refs(project, executor)
    message = send_message(
        project_id=project.pk,
        actor=executor,
        client_message_id=uuid4(),
        content="The customer approved the first launch window.",
    ).message
    foreign_message = send_message(
        project_id=other_project.pk,
        actor=outsider,
        client_message_id=uuid4(),
        content="This message belongs to another project.",
    ).message

    conflict = create_project_conflict(
        project_id=project.pk,
        actor=executor,
        data={
            "title": "Chat-backed evidence",
            "evidence_refs": [
                questionnaire_refs[0],
                {"source_type": "message", "source_id": message.pk},
            ],
        },
    )
    message_evidence = conflict.evidence.get(source_type="message")
    assert message_evidence.source_id == message.pk
    assert message_evidence.excerpt == message.content
    assert message_evidence.metadata == {
        "message_type": "text",
        "sender_id": str(executor.pk),
        "sent_at": message.created_at.isoformat(),
    }

    for source_id in (uuid4(), foreign_message.pk):
        with pytest.raises(ProjectStateNotFoundError):
            create_project_conflict(
                project_id=project.pk,
                actor=executor,
                data={
                    "title": "Unavailable message source",
                    "evidence_refs": [
                        questionnaire_refs[0],
                        {"source_type": "message", "source_id": source_id},
                    ],
                },
            )


@pytest.mark.django_db
def test_creation_validation_and_position_constraint(project_context):
    project, executor, _, _, _ = project_context
    with pytest.raises(ValidationError):
        create_project_stage(project_id=project.pk, actor=executor, data={"name": " "})
    stage = create_project_stage(
        project_id=project.pk,
        actor=executor,
        data={"name": "Dated stage", "position": 1, "start_date": date(2026, 11, 12)},
    )
    assert stage.position == 1
    assert stage.start_date == date(2026, 11, 12)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("model", "fields"),
    [
        (ProjectStage, {"name": "Stage", "status": "invalid"}),
        (Requirement, {"title": "Requirement", "status": "invalid"}),
        (Task, {"title": "Task", "status": "invalid"}),
        (OpenQuestion, {"question": "Question?", "status": "invalid"}),
        (ProjectConflict, {"title": "Conflict", "status": "invalid"}),
    ],
)
def test_database_constraints_reject_unsupported_status_values(
    project_context, model, fields
):
    project, executor, _, _, _ = project_context

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            model.objects.create(project=project, created_by=executor, **fields)


@pytest.mark.django_db
def test_evidence_and_conflict_link_constraints_enforce_immutable_sources(
    project_context,
):
    project, executor, _, _, _ = project_context
    conflict = create_project_conflict(
        project_id=project.pk,
        actor=executor,
        data={"title": "Conflict", "evidence_refs": _evidence_refs(project, executor)},
    )
    evidence = conflict.evidence.first()

    evidence.excerpt = "edited evidence"
    with pytest.raises(ValidationError):
        evidence.save()
    with pytest.raises(ValidationError):
        evidence.delete()
    with pytest.raises(ValidationError):
        Evidence.objects.filter(pk=evidence.pk).update(excerpt="edited evidence")
    with pytest.raises(ValidationError):
        Evidence.objects.filter(pk=evidence.pk).delete()
    with pytest.raises(ValidationError):
        Evidence.objects.bulk_update([evidence], ["excerpt"])

    link = conflict.evidence_links.first()
    other_evidence = conflict.evidence.exclude(pk=link.evidence_id).first()
    link.evidence_id = other_evidence.pk
    with pytest.raises(ValidationError):
        link.save()
    with pytest.raises(ValidationError):
        link.delete()
    with pytest.raises(ValidationError):
        ProjectConflictEvidence.objects.filter(pk=link.pk).update(
            evidence_id=other_evidence.pk
        )
    with pytest.raises(ValidationError):
        ProjectConflictEvidence.objects.filter(pk=link.pk).delete()
    with pytest.raises(ValidationError):
        ProjectConflictEvidence.objects.bulk_update([link], ["evidence"])
    with pytest.raises(ValidationError):
        with transaction.atomic():
            conflict.evidence.remove(link.evidence_id)
    assert not transaction.get_rollback()
    with pytest.raises(ValidationError):
        with transaction.atomic():
            conflict.evidence.clear()
    assert not transaction.get_rollback()
    second_conflict = create_project_conflict(
        project_id=project.pk,
        actor=executor,
        data={
            "title": "Another conflict",
            "evidence_refs": _evidence_refs(project, executor),
        },
    )
    with pytest.raises(ValidationError):
        with transaction.atomic():
            conflict.evidence.add(second_conflict.evidence.first())
    assert not transaction.get_rollback()

    with pytest.raises(ValidationError):
        ProjectConflictEvidence.objects.create(conflict=conflict, evidence=evidence)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Evidence.objects.create(
                project=project,
                source_type="unsupported",
                source_id=uuid4(),
                excerpt="",
            )


@pytest.mark.django_db
def test_evidence_positional_bulk_create_upsert_cannot_mutate_snapshot(
    project_context,
):
    project, executor, _, _, _ = project_context
    conflict = create_project_conflict(
        project_id=project.pk,
        actor=executor,
        data={"title": "Conflict", "evidence_refs": _evidence_refs(project, executor)},
    )
    evidence = conflict.evidence.first()
    original_excerpt = evidence.excerpt
    replacement = Evidence(
        id=evidence.pk,
        project=project,
        source_type=evidence.source_type,
        source_id=evidence.source_id,
        excerpt="Changed through positional upsert",
        metadata=evidence.metadata,
    )

    with pytest.raises(ValidationError):
        Evidence.objects.bulk_create(
            [replacement], None, False, True, ["excerpt"], ["id"]
        )

    evidence.refresh_from_db()
    assert evidence.excerpt == original_excerpt
