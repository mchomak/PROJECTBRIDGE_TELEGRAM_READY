from django.urls import path

from .views import (
    ArchiveProjectView,
    CompleteProjectView,
    ProjectDetailView,
    ProjectListCreateView,
    ProjectMemberListView,
    ProjectPassportView,
    ReopenProjectView,
    RestoreProjectView,
)

app_name = "projects"

urlpatterns = [
    path("", ProjectListCreateView.as_view(), name="project-list"),
    path("<uuid:project_id>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "<uuid:project_id>/members/",
        ProjectMemberListView.as_view(),
        name="project-members",
    ),
    path(
        "<uuid:project_id>/complete/",
        CompleteProjectView.as_view(),
        name="project-complete",
    ),
    path(
        "<uuid:project_id>/reopen/",
        ReopenProjectView.as_view(),
        name="project-reopen",
    ),
    path(
        "<uuid:project_id>/archive/",
        ArchiveProjectView.as_view(),
        name="project-archive",
    ),
    path(
        "<uuid:project_id>/restore/",
        RestoreProjectView.as_view(),
        name="project-restore",
    ),
    path(
        "<uuid:project_id>/passport/",
        ProjectPassportView.as_view(),
        name="project-passport",
    ),
]
