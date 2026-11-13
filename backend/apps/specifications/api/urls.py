from django.urls import path

from .views import ProjectSpecificationGenerateView, ProjectSpecificationView

app_name = "specifications"

urlpatterns = [
    path(
        "projects/<uuid:project_id>/specification/",
        ProjectSpecificationView.as_view(),
        name="project-specification",
    ),
    path(
        "projects/<uuid:project_id>/specification/generate/",
        ProjectSpecificationGenerateView.as_view(),
        name="project-specification-generate",
    ),
]
