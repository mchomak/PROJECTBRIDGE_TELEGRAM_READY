from django.urls import path

from .core.views import (
    CsrfView,
    CurrentUserView,
    LoginView,
    LogoutView,
    RegisterView,
)

app_name = "accounts_core"

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="csrf"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("register/", RegisterView.as_view(), name="register"),
]
