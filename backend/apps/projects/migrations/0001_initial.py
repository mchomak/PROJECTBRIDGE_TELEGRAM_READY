import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "project_type",
                    models.CharField(
                        choices=[
                            ("website", "Website"),
                            ("telegram_bot", "Telegram bot"),
                            ("automation", "Automation"),
                            ("other", "Other"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("completed", "Completed"),
                            ("archived", "Archived"),
                        ],
                        default="draft",
                        max_length=16,
                    ),
                ),
                (
                    "status_before_archive",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("completed", "Completed"),
                        ],
                        max_length=16,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_projects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ProjectPassport",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("goal", models.TextField(blank=True, default="")),
                ("target_audience", models.TextField(blank=True, default="")),
                ("expected_result", models.TextField(blank=True, default="")),
                ("functional_scope", models.JSONField(default=dict)),
                ("integrations", models.JSONField(default=dict)),
                ("constraints", models.JSONField(default=dict)),
                ("deadline", models.DateField(blank=True, null=True)),
                (
                    "budget_min",
                    models.DecimalField(
                        blank=True, decimal_places=10, max_digits=30, null=True
                    ),
                ),
                (
                    "budget_max",
                    models.DecimalField(
                        blank=True, decimal_places=10, max_digits=30, null=True
                    ),
                ),
                ("currency", models.CharField(blank=True, max_length=3, null=True)),
                ("additional_data", models.JSONField(default=dict)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="passport",
                        to="projects.project",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ProjectMember",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[("executor", "Executor"), ("customer", "Customer")],
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("left", "Left"),
                            ("revoked", "Revoked"),
                        ],
                        default="active",
                        max_length=16,
                    ),
                ),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="projects.project",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="project_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
