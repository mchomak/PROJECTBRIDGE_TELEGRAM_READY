from channels.generic.websocket import AsyncJsonWebsocketConsumer


class HealthConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send_json({"status": "ok"})
        await self.close(code=1000)
