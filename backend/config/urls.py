from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/v1/health/", include("apps.health.urls")),
    path("api/v1/auth/", include("apps.accounts.api.urls")),
    path("api/v1/invitations/", include("apps.invitations.api.public_urls")),
    path("api/v1/questionnaire/", include("apps.questionnaire.api.urls")),
    path("api/v1/", include("apps.project_state.api.urls")),
    path("api/v1/projects/", include("apps.projects.api.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="docs",
        ),
    ]
