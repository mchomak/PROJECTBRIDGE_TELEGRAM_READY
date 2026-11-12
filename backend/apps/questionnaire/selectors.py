from .models import (
    QuestionnaireAnswer,
    QuestionnaireSubmission,
    QuestionnaireSubmissionStatus,
)


def get_draft_for_project(*, project_id):
    return (
        QuestionnaireSubmission.objects.filter(
            project_id=project_id,
            status=QuestionnaireSubmissionStatus.DRAFT,
        )
        .prefetch_related("answers")
        .first()
    )


def get_submissions_for_project(*, project_id):
    return QuestionnaireSubmission.objects.filter(
        project_id=project_id
    ).prefetch_related("answers")


def get_answers_for_submission(*, submission_id):
    return {
        answer.question_key: answer
        for answer in QuestionnaireSubmission.objects.get(
            pk=submission_id
        ).answers.all()
    }


def get_submitted_answer_evidence_options(*, project_id):
    """Return immutable, project-owned questionnaire answer sources for evidence."""
    return (
        QuestionnaireAnswer.objects.filter(
            submission__project_id=project_id,
            submission__status=QuestionnaireSubmissionStatus.SUBMITTED,
        )
        .select_related("submission")
        .order_by("submission__submitted_at", "question_key", "id")
    )


def get_submitted_answer_for_evidence(*, project_id, answer_id):
    """Resolve one submitted answer only when it belongs to the supplied project."""
    return (
        QuestionnaireAnswer.objects.filter(
            pk=answer_id,
            submission__project_id=project_id,
            submission__status=QuestionnaireSubmissionStatus.SUBMITTED,
        )
        .select_related("submission")
        .first()
    )
