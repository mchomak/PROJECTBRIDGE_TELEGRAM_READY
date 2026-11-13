from django.db import migrations


def seed_profiles(apps, schema_editor):
    Profile = apps.get_model("ai_assistant", "AIModelProfile")
    database = schema_editor.connection.alias

    profiles = [
        {
            "profile_key": "message-analysis-luna",
            "task_key": "message_analysis",
            "provider_key": "openai",
            "model_name": "gpt-6-luna",
            "capabilities": ["text_generation"],
            "parameters": {
                "input_usd_per_million_tokens": "0.10",
                "output_usd_per_million_tokens": "0.50",
                "max_input_bytes": 32000,
                "max_output_tokens": 2048,
                "timeout_seconds": 30,
                "max_request_cost_usd": "0.25",
                "daily_budget_usd": "1.00",
            },
            "is_default": True,
            "is_enabled": True,
        },
        {
            "profile_key": "message-analysis-sol",
            "task_key": "message_analysis",
            "provider_key": "openai",
            "model_name": "gpt-6.1-sol",
            "capabilities": ["text_generation"],
            "parameters": {
                "input_usd_per_million_tokens": "2.00",
                "output_usd_per_million_tokens": "10.00",
                "max_input_bytes": 32000,
                "max_output_tokens": 2048,
                "timeout_seconds": 30,
                "max_request_cost_usd": "0.25",
                "daily_budget_usd": "1.00",
            },
            "is_default": False,
            "is_enabled": True,
        },
        {
            "profile_key": "conversation-analysis-sol",
            "task_key": "conversation_analysis",
            "provider_key": "openai",
            "model_name": "gpt-6.1-sol",
            "capabilities": ["text_generation"],
            "parameters": {
                "input_usd_per_million_tokens": "2.00",
                "output_usd_per_million_tokens": "10.00",
                "max_input_bytes": 32000,
                "max_output_tokens": 4096,
                "timeout_seconds": 45,
                "max_request_cost_usd": "0.25",
                "daily_budget_usd": "1.00",
            },
            "is_default": True,
            "is_enabled": True,
        },
        {
            "profile_key": "conversation-analysis-luna",
            "task_key": "conversation_analysis",
            "provider_key": "openai",
            "model_name": "gpt-6-luna",
            "capabilities": ["text_generation"],
            "parameters": {
                "input_usd_per_million_tokens": "0.10",
                "output_usd_per_million_tokens": "0.50",
                "max_input_bytes": 32000,
                "max_output_tokens": 4096,
                "timeout_seconds": 45,
                "max_request_cost_usd": "0.25",
                "daily_budget_usd": "1.00",
            },
            "is_default": False,
            "is_enabled": True,
        },
        {
            "profile_key": "contradiction-detection-sol",
            "task_key": "contradiction_detection",
            "provider_key": "openai",
            "model_name": "gpt-6.1-sol",
            "capabilities": ["text_generation"],
            "parameters": {
                "input_usd_per_million_tokens": "2.00",
                "output_usd_per_million_tokens": "10.00",
                "max_input_bytes": 32000,
                "max_output_tokens": 4096,
                "timeout_seconds": 45,
                "max_request_cost_usd": "0.25",
                "daily_budget_usd": "1.00",
            },
            "is_default": True,
            "is_enabled": True,
        },
        {
            "profile_key": "contradiction-detection-luna",
            "task_key": "contradiction_detection",
            "provider_key": "openai",
            "model_name": "gpt-6-luna",
            "capabilities": ["text_generation"],
            "parameters": {
                "input_usd_per_million_tokens": "0.10",
                "output_usd_per_million_tokens": "0.50",
                "max_input_bytes": 32000,
                "max_output_tokens": 4096,
                "timeout_seconds": 45,
                "max_request_cost_usd": "0.25",
                "daily_budget_usd": "1.00",
            },
            "is_default": False,
            "is_enabled": True,
        },
        {
            "profile_key": "document-embedding-small-1536",
            "task_key": "document_embedding",
            "provider_key": "openai",
            "model_name": "text-embedding-3-small",
            "capabilities": ["embeddings"],
            "parameters": {
                "dimensions": 1536,
                "input_usd_per_million_tokens": "0.02",
                "output_usd_per_million_tokens": "0",
                "max_input_bytes": 3000000,
                "max_output_tokens": 0,
                "timeout_seconds": 60,
                "max_request_cost_usd": "0.10",
                "daily_budget_usd": "1.00",
            },
            "is_default": True,
            "is_enabled": True,
        },
        {
            "profile_key": "rag-reranking-disabled",
            "task_key": "rag_reranking",
            "provider_key": "openai",
            "model_name": "",
            "capabilities": [],
            "parameters": {},
            "is_default": True,
            "is_enabled": False,
        },
        {
            "profile_key": "specification-generation-sol",
            "task_key": "specification_generation",
            "provider_key": "openai",
            "model_name": "gpt-6.1-sol",
            "capabilities": ["text_generation"],
            "parameters": {
                "input_usd_per_million_tokens": "2.00",
                "output_usd_per_million_tokens": "10.00",
                "max_input_bytes": 32000,
                "max_output_tokens": 8192,
                "timeout_seconds": 60,
                "max_request_cost_usd": "0.25",
                "daily_budget_usd": "1.00",
            },
            "is_default": True,
            "is_enabled": True,
        },
        {
            "profile_key": "specification-generation-luna",
            "task_key": "specification_generation",
            "provider_key": "openai",
            "model_name": "gpt-6-luna",
            "capabilities": ["text_generation"],
            "parameters": {
                "input_usd_per_million_tokens": "0.10",
                "output_usd_per_million_tokens": "0.50",
                "max_input_bytes": 32000,
                "max_output_tokens": 8192,
                "timeout_seconds": 60,
                "max_request_cost_usd": "0.25",
                "daily_budget_usd": "1.00",
            },
            "is_default": False,
            "is_enabled": True,
        },
    ]
    for fields in profiles:
        Profile.objects.using(database).update_or_create(
            profile_key=fields["profile_key"], defaults=fields
        )

    fallback_keys = {
        "message-analysis-luna": "message-analysis-sol",
        "conversation-analysis-sol": "conversation-analysis-luna",
        "contradiction-detection-sol": "contradiction-detection-luna",
        "specification-generation-sol": "specification-generation-luna",
    }
    for primary_key, fallback_key in fallback_keys.items():
        primary = Profile.objects.using(database).get(profile_key=primary_key)
        primary.fallback_profile = Profile.objects.using(database).get(
            profile_key=fallback_key
        )
        primary.save(using=database, update_fields=("fallback_profile",))


def remove_profiles(apps, schema_editor):
    Profile = apps.get_model("ai_assistant", "AIModelProfile")
    Profile.objects.using(schema_editor.connection.alias).filter(
        profile_key__in=(
            "message-analysis-luna",
            "message-analysis-sol",
            "conversation-analysis-sol",
            "conversation-analysis-luna",
            "contradiction-detection-sol",
            "contradiction-detection-luna",
            "document-embedding-small-1536",
            "rag-reranking-disabled",
            "specification-generation-sol",
            "specification-generation-luna",
        )
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("ai_assistant", "0001_initial")]

    operations = [migrations.RunPython(seed_profiles, remove_profiles)]
