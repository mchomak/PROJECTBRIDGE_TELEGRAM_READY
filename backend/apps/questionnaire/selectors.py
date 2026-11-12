from .models import QuestionnaireSubmission, QuestionnaireSubmissionStatus


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
