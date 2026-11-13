from django.db import migrations, models


def mark_previous_dispatches_as_accepted(apps, schema_editor):
    request_model = apps.get_model("ai_assistant", "AIAnalysisRequest")
    request_model.objects.filter(dispatch_attempts__gt=0).update(
        dispatch_successful_at=models.F("created_at")
    )


class Migration(migrations.Migration):
    dependencies = [("ai_assistant", "0008_analysis_dispatch_recovery")]

    operations = [
        migrations.AlterField(
            model_name="aianalysisrequest",
            name="dispatch_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="aianalysisrequest",
            name="dispatch_failures",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="aianalysisrequest",
            name="dispatch_successful_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            mark_previous_dispatches_as_accepted,
            migrations.RunPython.noop,
        ),
    ]
