"""REST API for the weighing stage."""
from django.db import models

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.auth import LanAccess
from apps.core.live import LIVE_GROUP
from apps.tournaments.models import Tournament

from .models import Participant, WeighIn
from .serializers import ParticipantSerializer, WeighInSerializer
from .services import record_weigh_in


def _active_tournament() -> Tournament:
    return Tournament.objects.order_by("id").first()


class ParticipantViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ParticipantSerializer
    permission_classes = [LanAccess]

    def get_queryset(self):
        return Participant.objects.select_related(
            "club", "age_group", "weight_category"
        ).all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(last_name__icontains=search)
                | models.Q(first_name__icontains=search)
                | models.Q(middle_name__icontains=search)
                | models.Q(club__name__icontains=search)
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class WeighInViewSet(viewsets.ViewSet):
    permission_classes = [LanAccess]

    def list(self, request):
        queryset = WeighIn.objects.select_related(
            "participant__club", "participant__weight_category"
        ).order_by("participant__last_name")
        return Response(
            WeighInSerializer(queryset, many=True).data
        )

    def create(self, request):
        tournament = _active_tournament()
        data = request.data
        participant_id = data.get("participant_id")
        try:
            participant = tournament.participants.get(pk=participant_id)
        except Participant.DoesNotExist:
            return Response(
                {"error": "Участник не найден"}, status=status.HTTP_404_NOT_FOUND
            )
        weigh_in = record_weigh_in(
            participant,
            current_weight=data.get("current_weight"),
            passed=bool(data.get("passed", True)),
            weighed_by=data.get("weighed_by", ""),
            note=data.get("note", ""),
        )
        return Response(WeighInSerializer(weigh_in).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def progress(self, request):
        tournament = _active_tournament()
        total = tournament.participants.count()
        passed = tournament.weigh_ins.filter(passed=True).count()
        return Response(
            {
                "total": total,
                "done": passed,
                "remaining": total - passed,
                "group": LIVE_GROUP,
            }
        )
