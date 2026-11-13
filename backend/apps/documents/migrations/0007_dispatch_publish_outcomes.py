from django.db import migrations, models


def mark_previous_dispatches_as_accepted(apps, schema_editor):
    document_model = apps.get_model("documents", "Document")
    document_model.objects.filter(processing_dispatch_attempts__gt=0).update(
        processing_dispatch_successful_at=models.F("created_at")
    )


class Migration(migrations.Migration):
    dependencies = [("documents", "0006_processing_dispatch_recovery")]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="processing_dispatch_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="document",
            name="processing_dispatch_failures",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="document",
            name="processing_dispatch_successful_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            mark_previous_dispatches_as_accepted,
            migrations.RunPython.noop,
        ),
    ]
