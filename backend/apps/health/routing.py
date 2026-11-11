from django.urls import path

from .consumers import HealthConsumer

websocket_urlpatterns = [
    path("ws/v1/health/", HealthConsumer.as_asgi()),
]
