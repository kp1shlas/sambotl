"""Live (WebSocket) helpers.

All tournament clients (weighing, referees, scoreboards, schedule screens)
subscribe to a single broadcast group. Any server-side change calls
:func:`broadcast` and every connected screen updates instantly — no polling,
which matters on an unstable LAN.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

LIVE_GROUP = "tournament_live"
EVENT_TYPE = "tournament.event"


def broadcast(payload: dict) -> None:
    """Send ``payload`` to every connected live client (best effort)."""
    layer = get_channel_layer()
    if layer is None:  # channels not configured (e.g. plain WSGI test run)
        return
    try:
        async_to_sync(layer.group_send)(LIVE_GROUP, {"type": EVENT_TYPE, "payload": payload})
    except Exception:  # pragma: no cover - live updates must never break writes
        logger.exception("Не удалось отправить live-событие: %s", payload)
