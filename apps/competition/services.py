"""Bout control logic shared by the API (referee screen) and future admin actions."""
from django.utils import timezone

from apps.core import live
from apps.core.enums import BoutStatus


def _broadcast_bout(bout) -> None:
    duration = None
    try:
        duration = bout.tournament.bout_duration
    except Exception:  # pragma: no cover - defensive
        duration = None
    live.broadcast(
        {
            "type": "bout.updated",
            "bout_id": bout.pk,
            "mat": bout.mat.number if bout.mat_id else None,
            "round_no": bout.round_no,
            "order_in_mat": bout.order_in_mat,
            "status": bout.status,
            "score_a": bout.score_a,
            "score_b": bout.score_b,
            "warnings_a": bout.warnings_a,
            "warnings_b": bout.warnings_b,
            "a": bout.label("A"),
            "b": bout.label("B"),
            "winner_side": bout.winner_side,
            "result_text": bout.result_text,
            "started_at": bout.started_at.isoformat() if bout.started_at else None,
            "finished_at": bout.finished_at.isoformat() if bout.finished_at else None,
            "duration": duration,
        }
    )


def start_bout(bout) -> dict:
    """Put a bout on the mat and start its clock."""
    bout.status = BoutStatus.ON_MAT
    if not bout.started_at:
        bout.started_at = timezone.now()
    bout.save(update_fields=["status", "started_at", "updated_at"])
    _broadcast_bout(bout)
    return {"status": bout.status, "started_at": bout.started_at.isoformat()}


def add_score(bout, side: str, value: int) -> dict:
    """Add ``value`` points to side ``A`` or ``B`` and log the event."""
    from .models import BoutEvent

    if side not in ("A", "B"):
        raise ValueError("Сторона должна быть 'A' или 'B'")
    if side == "A":
        bout.score_a += int(value)
    else:
        bout.score_b += int(value)
    bout.save(update_fields=["score_a", "score_b", "updated_at"])
    BoutEvent.objects.create(
        bout=bout, kind=BoutEvent.Kind.SCORE, side=side, value=str(value)
    )
    _broadcast_bout(bout)
    return {"score_a": bout.score_a, "score_b": bout.score_b}


def add_warning(bout, side: str) -> dict:
    from .models import BoutEvent

    if side == "A":
        bout.warnings_a += 1
    else:
        bout.warnings_b += 1
    bout.save(update_fields=["warnings_a", "warnings_b", "updated_at"])
    BoutEvent.objects.create(
        bout=bout, kind=BoutEvent.Kind.WARNING, side=side, value="1"
    )
    _broadcast_bout(bout)
    return {"warnings_a": bout.warnings_a, "warnings_b": bout.warnings_b}


def finish_bout(bout, winner_side: str = "", result_text: str = "") -> dict:
    """End the bout, record the winner side and the textual result."""
    from .models import BoutEvent

    bout.status = BoutStatus.FINISHED
    bout.finished_at = timezone.now()
    if winner_side in ("A", "B"):
        bout.winner_side = winner_side
        bout.winner = (
            bout.participant_a if winner_side == "A" else bout.participant_b
        )
    bout.result_text = result_text
    bout.save(
        update_fields=[
            "status",
            "finished_at",
            "winner_side",
            "winner",
            "result_text",
            "updated_at",
        ]
    )
    BoutEvent.objects.create(
        bout=bout,
        kind=BoutEvent.Kind.RESULT,
        side=winner_side,
        value=result_text,
    )
    _broadcast_bout(bout)
    return {"status": bout.status, "winner_side": bout.winner_side}
