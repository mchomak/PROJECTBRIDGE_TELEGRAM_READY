from channels.auth import AuthMiddlewareStack
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.urls import path

from .consumers import ProjectChatConsumer

websocket_origins = list(
    dict.fromkeys(
        origin.rstrip("/")
        for origin in [settings.FRONTEND_BASE_URL, *settings.CSRF_TRUSTED_ORIGINS]
        if origin
    )
)

chat_websocket_urlpatterns = [
    path(
        "ws/v1/projects/<uuid:project_id>/chat/",
        OriginValidator(
            AuthMiddlewareStack(ProjectChatConsumer.as_asgi()),
            websocket_origins,
        ),
    ),
]
