from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("projects", "0001_initial")]

    operations = [
        migrations.AddConstraint(
            model_name="project",
            constraint=models.CheckConstraint(
                condition=Q(
                    project_type__in=("website", "telegram_bot", "automation", "other")
                ),
                name="project_type_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.CheckConstraint(
                condition=Q(status__in=("draft", "active", "completed", "archived")),
                name="project_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.CheckConstraint(
                condition=Q(status_before_archive__isnull=True)
                | Q(status_before_archive__in=("draft", "active", "completed")),
                name="project_prev_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.CheckConstraint(
                condition=(
                    Q(
                        status="archived",
                        status_before_archive__isnull=False,
                        archived_at__isnull=False,
                    )
                    | (
                        ~Q(status="archived")
                        & Q(
                            status_before_archive__isnull=True,
                            archived_at__isnull=True,
                        )
                    )
                ),
                name="project_archive_consistent",
            ),
        ),
        migrations.AddConstraint(
            model_name="projectmember",
            constraint=models.UniqueConstraint(
                fields=("project", "user"),
                name="unique_project_user_membership",
            ),
        ),
        migrations.AddConstraint(
            model_name="projectmember",
            constraint=models.UniqueConstraint(
                condition=Q(status="active"),
                fields=("project", "role"),
                name="one_active_project_role",
            ),
        ),
        migrations.AddConstraint(
            model_name="projectmember",
            constraint=models.CheckConstraint(
                condition=Q(role__in=("executor", "customer")),
                name="project_member_role_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="projectmember",
            constraint=models.CheckConstraint(
                condition=Q(status__in=("active", "left", "revoked")),
                name="project_member_status_valid",
            ),
        ),
    ]
