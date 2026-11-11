from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator

from config.asgi import application


def test_health_websocket_accepts_sends_status_and_closes():
    async def connect_and_check():
        communicator = WebsocketCommunicator(application, "/ws/v1/health/")
        connected, _ = await communicator.connect()

        assert connected
        assert await communicator.receive_json_from() == {"status": "ok"}
        assert await communicator.receive_output() == {
            "type": "websocket.close",
            "code": 1000,
        }
        await communicator.wait()

    async_to_sync(connect_and_check)()
