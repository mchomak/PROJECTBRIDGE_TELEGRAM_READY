from apps.project_state.selectors import (
    get_project_conflicts_for_member,
    get_project_open_questions_for_member,
    get_project_requirements_for_member,
    get_project_stages_for_member,
    get_project_tasks_for_member,
)
from apps.projects.selectors import get_passport_for_member

from .models import SpecificationGenerationRequest

STAGE_AUTHORITY_NOTES = {
    "planned": "Planned stage; this is future work, not a completed fact.",
    "active": "Active shared delivery stage.",
    "blocked": "Blocked shared delivery stage; preserve its blocked status.",
    "completed": "Completed shared delivery milestone.",
    "cancelled": "CANCELLED: exclude from the current delivery plan.",
}
REQUIREMENT_AUTHORITY_NOTES = {
    "draft": "DRAFT UNCONFIRMED: not an approved or committed requirement.",
    "confirmed": "CONFIRMED shared requirement.",
    "in_progress": "CONFIRMED shared requirement; currently in progress.",
    "blocked": "CONFIRMED shared requirement; currently blocked.",
    "completed": "CONFIRMED shared requirement; marked completed.",
    "rejected": "REJECTED: exclude from current requirements and commitments.",
}
TASK_AUTHORITY_NOTES = {
    "todo": "Planned implementation task; not itself an approved requirement.",
    "in_progress": "Implementation task currently in progress.",
    "blocked": "Implementation task currently blocked.",
    "done": "Implementation task marked done; do not present as future work.",
    "cancelled": "CANCELLED: exclude from the current delivery plan.",
}


def get_latest_generation_for_member(*, project_id, actor):
    return (
        SpecificationGenerationRequest.objects.filter(
            project_id=project_id,
            project__memberships__user=actor,
            project__memberships__status="active",
        )
        .distinct()
        .first()
    )


def get_specification_generation_context(*, project, actor):
    """Build a minimal shared-source snapshot; never reads AI-private records."""
    passport = get_passport_for_member(project_id=project.pk, user=actor)
    if passport is None:
        passport_data = None
    else:
        passport_data = {
            "goal": passport.goal,
            "target_audience": passport.target_audience,
            "expected_result": passport.expected_result,
            "functional_scope": passport.functional_scope,
            "integrations": passport.integrations,
            "constraints": passport.constraints,
            "deadline": passport.deadline.isoformat() if passport.deadline else None,
            "budget_min": str(passport.budget_min)
            if passport.budget_min is not None
            else None,
            "budget_max": str(passport.budget_max)
            if passport.budget_max is not None
            else None,
            "currency": passport.currency,
            "additional_data": passport.additional_data,
        }

    stages = [
        {
            "name": item.name,
            "description": item.description,
            "status": item.status,
            "authority_note": STAGE_AUTHORITY_NOTES[item.status],
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "due_date": item.due_date.isoformat() if item.due_date else None,
        }
        for item in get_project_stages_for_member(
            project_id=project.pk, actor=actor
        ).order_by("position", "id")
    ]
    requirements = [
        {
            "title": item.title,
            "description": item.description,
            "status": item.status,
            "authority_note": REQUIREMENT_AUTHORITY_NOTES[item.status],
        }
        for item in get_project_requirements_for_member(
            project_id=project.pk, actor=actor
        ).order_by("created_at", "id")
    ]
    tasks = [
        {
            "title": item.title,
            "description": item.description,
            "status": item.status,
            "authority_note": TASK_AUTHORITY_NOTES[item.status],
            "due_date": item.due_date.isoformat() if item.due_date else None,
        }
        for item in get_project_tasks_for_member(
            project_id=project.pk, actor=actor
        ).order_by("due_date", "created_at", "id")
    ]
    questions = [
        {
            "question": item.question,
            "answer": item.answer,
            "status": item.status,
            "authority_note": {
                "open": "UNRESOLVED: do not present as a settled decision.",
                "resolved": "Resolved shared project-state answer.",
                "dismissed": (
                    "DISMISSED: this question was not adopted as a decision or fact."
                ),
            }[item.status],
        }
        for item in get_project_open_questions_for_member(
            project_id=project.pk, actor=actor
        ).order_by("created_at", "id")
    ]
    conflicts = []
    for item in get_project_conflicts_for_member(
        project_id=project.pk, actor=actor
    ).order_by("created_at", "id"):
        conflict = {
            "status": item.status,
            "authority_note": {
                "unresolved": (
                    "UNRESOLVED CONTRADICTION: neither side is established as fact."
                ),
                "resolved": (
                    "Resolved shared conflict; use only its recorded resolution."
                ),
                "dismissed": (
                    "DISMISSED: neither conflicting claim was adopted as fact."
                ),
            }[item.status],
        }
        if item.status == "resolved":
            conflict["resolution"] = item.resolution
        else:
            conflict["title"] = item.title
            conflict["description"] = item.description
            conflict["resolution"] = ""
        conflicts.append(conflict)
    return {
        "passport": passport_data,
        "project_state": {
            "stages": stages,
            "requirements": requirements,
            "tasks": tasks,
            "questions": questions,
            "conflicts": conflicts,
        },
        "source_policy": (
            "Only this approved passport and shared Project State are sources. "
            "Do not infer missing facts. Pending AI proposals, internal analyses, "
            "documents, chat, and RAG are excluded."
        ),
    }
