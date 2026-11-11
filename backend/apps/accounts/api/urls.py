from django.urls import include, path

app_name = "accounts"

urlpatterns = [
    path("", include("apps.accounts.api.core_urls")),
    path("", include("apps.accounts.api.verification_urls")),
]
