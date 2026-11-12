from django.urls import path

from .views import (
    DocumentDetailView,
    DocumentDownloadView,
    DocumentLifecycleRequestCreateView,
    DocumentRestoreView,
)

app_name = "documents"

urlpatterns = [
    path(
        "<uuid:document_id>/lifecycle-requests/",
        DocumentLifecycleRequestCreateView.as_view(),
        name="document-lifecycle-request-create",
    ),
    path(
        "<uuid:document_id>/restore/",
        DocumentRestoreView.as_view(),
        name="document-restore",
    ),
    path(
        "<uuid:document_id>/download/",
        DocumentDownloadView.as_view(),
        name="document-download",
    ),
    path("<uuid:document_id>/", DocumentDetailView.as_view(), name="document-detail"),
]
