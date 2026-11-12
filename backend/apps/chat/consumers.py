from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.projects.models import ProjectMember, ProjectMemberStatus

from .services import project_chat_group_name


@database_sync_to_async
def _has_active_membership(*, project_id, user_id):
    return ProjectMember.objects.filter(
        project_id=project_id,
        user_id=user_id,
        status=ProjectMemberStatus.ACTIVE,
    ).exists()


class ProjectChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
        if not await _has_active_membership(
            project_id=self.project_id,
            user_id=user.pk,
        ):
            await self.close(code=4403)
            return

        self.group_name = project_chat_group_name(self.project_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        if group_name is not None:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def chat_message_created(self, event):
        await self.send_json(
            {
                "type": "message.created",
                "message": event["message"],
            }
        )
