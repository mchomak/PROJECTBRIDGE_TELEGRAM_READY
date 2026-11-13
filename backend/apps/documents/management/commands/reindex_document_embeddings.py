from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.documents.services import queue_document_embedding_reindex
from apps.projects.models import Project


class Command(BaseCommand):
    help = "Queue a maintenance reindex of derived document chunks and embeddings."

    def add_arguments(self, parser):
        scope = parser.add_mutually_exclusive_group(required=True)
        scope.add_argument("--project-id", help="Reindex one project's documents.")
        scope.add_argument(
            "--all-projects",
            action="store_true",
            help="Reindex eligible documents across all projects.",
        )

    def handle(self, *args, **options):
        project_id = options["project_id"]
        if project_id:
            try:
                project_id = UUID(project_id)
            except ValueError as exc:
                raise CommandError("--project-id must be a UUID.") from exc
            if not Project.objects.filter(pk=project_id).exists():
                raise CommandError("Project does not exist.")

        queued_count = queue_document_embedding_reindex(project_id=project_id)
        self.stdout.write(
            self.style.SUCCESS(
                f"Queued {queued_count} eligible document reindex task(s)."
            )
        )
