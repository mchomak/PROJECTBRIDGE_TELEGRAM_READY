from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0007_dispatch_publish_outcomes")]

    operations = [
        migrations.AddField(
            model_name="document",
            name="processing_dispatch_error_code",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
