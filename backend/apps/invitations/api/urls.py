from django.urls import path

from .views import ProjectInvitationListCreateView, ProjectInvitationRevokeView

app_name = "invitations"

urlpatterns = [
    path("", ProjectInvitationListCreateView.as_view(), name="project-invitations"),
    path(
        "<uuid:invitation_id>/revoke/",
        ProjectInvitationRevokeView.as_view(),
        name="project-invitation-revoke",
    ),
]
