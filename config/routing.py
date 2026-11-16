"""WebSocket routes.

The whole tournament shares a single broadcast group ``tournament_live``:
weighing progress, current bouts, mat timers and scoreboards all push
updates through it, so all LAN clients stay in sync in real time.
"""
from django.urls import path

from apps.core.consumers import TournamentLiveConsumer

websocket_urlpatterns = [
    path("ws/live/", TournamentLiveConsumer.as_asgi()),
]
