from django.urls import path

from .views import ProjectMessagesView

app_name = "chat"

urlpatterns = [path("", ProjectMessagesView.as_view(), name="project-messages")]
