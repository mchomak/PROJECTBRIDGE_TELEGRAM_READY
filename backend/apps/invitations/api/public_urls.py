from django.urls import path

from .views import InvitationAcceptView, PublicInvitationPreviewView

app_name = "public_invitations"

urlpatterns = [
    path("preview/", PublicInvitationPreviewView.as_view(), name="preview"),
    path("accept/", InvitationAcceptView.as_view(), name="accept"),
]
