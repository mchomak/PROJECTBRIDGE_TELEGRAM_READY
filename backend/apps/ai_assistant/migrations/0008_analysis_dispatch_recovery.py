from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ai_assistant", "0007_aianalysisrequest_idempotency_key_and_more")]

    operations = [
        migrations.AddField(
            model_name="aianalysisrequest",
            name="dispatch_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="aianalysisrequest",
            name="dispatch_lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
