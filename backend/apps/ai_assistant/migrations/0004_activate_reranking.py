from django.db import migrations


def activate_reranking(apps, schema_editor):
    Profile = apps.get_model("ai_assistant", "AIModelProfile")
    database = schema_editor.connection.alias
    primary = Profile.objects.using(database).get(profile_key="rag-reranking-disabled")
    primary.profile_key = "rag-reranking-sol"
    primary.model_name = "gpt-6.1-sol"
    primary.capabilities = ["reranking"]
    primary.parameters = {
        "input_usd_per_million_tokens": "2.00",
        "output_usd_per_million_tokens": "10.00",
        "max_input_bytes": 32000,
        "max_candidates": 100,
        "max_output_tokens": 4096,
        "timeout_seconds": 45,
        "max_request_cost_usd": "0.25",
        "daily_budget_usd": "1.00",
    }
    primary.is_enabled = True
    primary.save(using=database)

    fallback, _ = Profile.objects.using(database).update_or_create(
        profile_key="rag-reranking-luna",
        defaults={
            "task_key": "rag_reranking",
            "provider_key": "openai",
            "model_name": "gpt-6-luna",
            "capabilities": ["reranking"],
            "parameters": {
                "input_usd_per_million_tokens": "0.10",
                "output_usd_per_million_tokens": "0.50",
                "max_input_bytes": 32000,
                "max_candidates": 100,
                "max_output_tokens": 4096,
                "timeout_seconds": 45,
                "max_request_cost_usd": "0.25",
                "daily_budget_usd": "1.00",
            },
            "is_default": False,
            "is_enabled": True,
        },
    )
    primary.fallback_profile = fallback
    primary.save(using=database, update_fields=("fallback_profile",))


def disable_reranking(apps, schema_editor):
    Profile = apps.get_model("ai_assistant", "AIModelProfile")
    database = schema_editor.connection.alias
    primary = Profile.objects.using(database).get(profile_key="rag-reranking-sol")
    primary.fallback_profile = None
    primary.profile_key = "rag-reranking-disabled"
    primary.model_name = ""
    primary.capabilities = []
    primary.parameters = {}
    primary.is_enabled = False
    primary.save(using=database)
    Profile.objects.using(database).filter(profile_key="rag-reranking-luna").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ai_assistant", "0003_aimodelprofile_embedding_space_version_and_more")
    ]

    operations = [migrations.RunPython(activate_reranking, disable_reranking)]
