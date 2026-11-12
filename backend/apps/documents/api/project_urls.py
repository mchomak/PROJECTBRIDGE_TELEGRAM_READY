from django.urls import path

from .views import ProjectDocumentListCreateView

app_name = "documents"

urlpatterns = [
    path("", ProjectDocumentListCreateView.as_view(), name="project-document-list"),
]
