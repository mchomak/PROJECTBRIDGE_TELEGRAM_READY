from django.urls import path

from .views import (
    AIAnalysisCollectionView,
    AIAnalysisDetailView,
    AIProposalAcceptView,
    AIProposalApplyEditedView,
    AIProposalCollectionView,
    AIProposalDetailView,
    AIProposalRejectView,
)

app_name = "ai_assistant"

urlpatterns = [
    path(
        "projects/<uuid:project_id>/ai/analyses/",
        AIAnalysisCollectionView.as_view(),
        name="analysis-list-create",
    ),
    path(
        "projects/<uuid:project_id>/ai/analyses/<uuid:request_id>/",
        AIAnalysisDetailView.as_view(),
        name="analysis-detail",
    ),
    path(
        "projects/<uuid:project_id>/ai/proposals/",
        AIProposalCollectionView.as_view(),
        name="proposal-list",
    ),
    path(
        "ai/proposals/<uuid:proposal_id>/",
        AIProposalDetailView.as_view(),
        name="proposal-detail",
    ),
    path(
        "ai/proposals/<uuid:proposal_id>/accept/",
        AIProposalAcceptView.as_view(),
        name="proposal-accept",
    ),
    path(
        "ai/proposals/<uuid:proposal_id>/reject/",
        AIProposalRejectView.as_view(),
        name="proposal-reject",
    ),
    path(
        "ai/proposals/<uuid:proposal_id>/apply-edited/",
        AIProposalApplyEditedView.as_view(),
        name="proposal-apply-edited",
    ),
]
