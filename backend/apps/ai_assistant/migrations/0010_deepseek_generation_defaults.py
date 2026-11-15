from django.db import migrations


PROFILE_KEYS = (
    "message-analysis-luna",
    "conversation-analysis-sol",
    "contradiction-detection-sol",
    "rag-reranking-sol",
    "specification-generation-sol",
)


def use_deepseek(apps, schema_editor):
    Profile = apps.get_model("ai_assistant", "AIModelProfile")
    database = schema_editor.connection.alias
    for profile in Profile.objects.using(database).filter(
        profile_key__in=PROFILE_KEYS
    ):
        profile.provider_key = "deepseek"
        profile.model_name = "deepseek-flash"
        profile.fallback_profile = None
        profile.parameters = {
            **profile.parameters,
            # Use peak rates for conservative local cost estimates.
            "input_usd_per_million_tokens": "0.30",
            "output_usd_per_million_tokens": "1.20",
        }
        profile.config_version += 1
        profile.save(
            using=database,
            update_fields=(
                "provider_key",
                "model_name",
                "fallback_profile",
                "parameters",
                "config_version",
                "updated_at",
            ),
        )


def restore_openai(apps, schema_editor):
    Profile = apps.get_model("ai_assistant", "AIModelProfile")
    database = schema_editor.connection.alias
    models = {
        "message-analysis-luna": ("gpt-6-luna", "0.10", "0.50", "message-analysis-sol"),
        "conversation-analysis-sol": (
            "gpt-6.1-sol",
            "2.00",
            "10.00",
            "conversation-analysis-luna",
        ),
        "contradiction-detection-sol": (
            "gpt-6.1-sol",
            "2.00",
            "10.00",
            "contradiction-detection-luna",
        ),
        "rag-reranking-sol": (
            "gpt-6.1-sol",
            "2.00",
            "10.00",
            "rag-reranking-luna",
        ),
        "specification-generation-sol": (
            "gpt-6.1-sol",
            "2.00",
            "10.00",
            "specification-generation-luna",
        ),
    }
    for key, (model, input_rate, output_rate, fallback_key) in models.items():
        profile = Profile.objects.using(database).get(profile_key=key)
        profile.provider_key = "openai"
        profile.model_name = model
        profile.fallback_profile = Profile.objects.using(database).get(
            profile_key=fallback_key
        )
        profile.parameters = {
            **profile.parameters,
            "input_usd_per_million_tokens": input_rate,
            "output_usd_per_million_tokens": output_rate,
        }
        profile.config_version += 1
        profile.save(
            using=database,
            update_fields=(
                "provider_key",
                "model_name",
                "fallback_profile",
                "parameters",
                "config_version",
                "updated_at",
            ),
        )


class Migration(migrations.Migration):
    dependencies = [("ai_assistant", "0009_dispatch_publish_outcomes")]

    operations = [migrations.RunPython(use_deepseek, restore_openai)]
