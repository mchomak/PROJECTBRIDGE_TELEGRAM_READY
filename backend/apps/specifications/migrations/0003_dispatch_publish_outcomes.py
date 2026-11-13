from django.db import migrations, models


def mark_previous_dispatches_as_accepted(apps, schema_editor):
    request_model = apps.get_model("specifications", "SpecificationGenerationRequest")
    request_model.objects.filter(dispatch_attempts__gt=0).update(
        dispatch_successful_at=models.F("created_at")
    )


class Migration(migrations.Migration):
    dependencies = [("specifications", "0002_generation_dispatch_recovery")]

    operations = [
        migrations.AlterField(
            model_name="specificationgenerationrequest",
            name="dispatch_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="specificationgenerationrequest",
            name="dispatch_failures",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="specificationgenerationrequest",
            name="dispatch_successful_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            mark_previous_dispatches_as_accepted,
            migrations.RunPython.noop,
        ),
    ]
