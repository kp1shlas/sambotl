from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.core.live import LIVE_GROUP


class TournamentLiveConsumer(AsyncJsonWebsocketConsumer):
    """Single fan-out channel for live tournament state.

    Expected payloads (``{"type": ...}``):
      * ``weighing.progress`` — how many athletes weighed in
      * ``bout.started`` / ``bout.finished`` / ``bout.score``
      * ``timer.tick`` — mat timer for scoreboard screens
    """

    async def connect(self) -> None:
        await self.channel_layer.group_add(LIVE_GROUP, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected", "group": LIVE_GROUP})

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(LIVE_GROUP, self.channel_name)

    async def tournament_event(self, event: dict) -> None:
        await self.send_json(event["payload"])
