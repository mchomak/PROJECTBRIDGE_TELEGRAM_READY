from django.urls import path

from .views import (
    DocumentLifecycleApproveView,
    DocumentLifecycleCancelView,
    DocumentLifecycleRejectView,
)

app_name = "document_lifecycle"

urlpatterns = [
    path("<uuid:request_id>/approve/", DocumentLifecycleApproveView.as_view()),
    path("<uuid:request_id>/reject/", DocumentLifecycleRejectView.as_view()),
    path("<uuid:request_id>/cancel/", DocumentLifecycleCancelView.as_view()),
]
