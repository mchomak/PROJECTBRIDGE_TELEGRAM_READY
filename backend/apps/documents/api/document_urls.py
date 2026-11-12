from django.urls import path

from .views import DocumentDetailView, DocumentDownloadView

app_name = "documents"

urlpatterns = [
    path(
        "<uuid:document_id>/download/",
        DocumentDownloadView.as_view(),
        name="document-download",
    ),
    path("<uuid:document_id>/", DocumentDetailView.as_view(), name="document-detail"),
]
