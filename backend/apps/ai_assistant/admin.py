from django.contrib import admin

from .models import AIAnalysisRun, AIModelProfile


@admin.register(AIModelProfile)
class AIModelProfileAdmin(admin.ModelAdmin):
    list_display = (
        "profile_key",
        "task_key",
        "provider_key",
        "model_name",
        "config_version",
        "embedding_space_version",
        "is_default",
        "is_enabled",
    )
    list_filter = ("task_key", "provider_key", "is_default", "is_enabled")
    search_fields = ("profile_key", "model_name")
    readonly_fields = ("config_version", "updated_at")
    ordering = ("task_key", "profile_key")


@admin.register(AIAnalysisRun)
class AIAnalysisRunAdmin(admin.ModelAdmin):
    list_display = (
        "task_key",
        "provider_key",
        "model_name",
        "profile_version",
        "status",
        "started_at",
        "estimated_cost",
        "reserved_cost",
    )
    list_filter = ("task_key", "provider_key", "status")
    search_fields = ("id", "input_hash")
    readonly_fields = tuple(field.name for field in AIAnalysisRun._meta.fields)
    date_hierarchy = "started_at"
    ordering = ("-started_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
