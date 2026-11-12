from django.urls import path

from .consumers import ProjectChatConsumer

chat_websocket_urlpatterns = [
    path(
        "ws/v1/projects/<uuid:project_id>/chat/",
        ProjectChatConsumer.as_asgi(),
    ),
]
