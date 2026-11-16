"""Weighing business logic shared by the API and the admin."""
from django.utils import timezone

from apps.core import live
from apps.core.enums import ParticipantStatus


def record_weigh_in(participant, *, current_weight, passed: bool, weighed_by: str = "", note: str = "") -> "WeighIn":
    """Create/update the weigh-in record and push the live progress event."""
    from .models import WeighIn

    weigh_in, _ = WeighIn.objects.update_or_create(
        participant=participant,
        defaults={
            "tournament": participant.tournament,
            "declared_weight": participant.declared_weight,
            "current_weight": current_weight,
            "passed": passed,
            "weighed_by": weighed_by,
            "weighed_at": timezone.now(),
            "note": note,
        },
    )
    participant.current_weight = current_weight
    participant.status = (
        ParticipantStatus.WEIGHED if passed else ParticipantStatus.WEIGH_FAILED
    )
    participant.save(update_fields=["current_weight", "status", "updated_at"])
    broadcast_weighing_progress(participant.tournament)
    return weigh_in


def broadcast_weighing_progress(tournament) -> None:
    total = tournament.participants.count()
    passed = tournament.weigh_ins.filter(passed=True).count()
    live.broadcast(
        {
            "type": "weighing.progress",
            "tournament": tournament.id,
            "total": total,
            "done": passed,
        }
    )
