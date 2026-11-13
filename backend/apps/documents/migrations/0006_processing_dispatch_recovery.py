from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0005_document_processing_generation")]

    operations = [
        migrations.AddField(
            model_name="document",
            name="processing_dispatch_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="document",
            name="processing_dispatch_lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="processing_lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
