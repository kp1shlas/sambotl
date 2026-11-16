"""Draw API: preview, generate, approve, and mat scheduling."""
import json

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core import live
from apps.core.auth import LanAccess
from apps.core.enums import BoutStatus, ParticipantStatus
from apps.participants.models import Participant
from apps.tournaments.models import Tournament

from .draw import STRATEGIES, build_bracket, generate_bouts
from .models import Bout, Bracket, Mat, WeightCategory
from .serializers import BoutSerializer, BracketSerializer, MatSerializer


def _tournament() -> Tournament:
    return Tournament.objects.order_by("id").first()


def _eligible(category: WeightCategory):
    """Athletes that may be drawn: weighed-in (or registered if no weighing run)."""
    queryset = Participant.objects.filter(weight_category=category)
    weighed = queryset.filter(status=ParticipantStatus.WEIGHED)
    return weighed if weighed.exists() else queryset.exclude(
        status=ParticipantStatus.WITHDRAWN
    )


class BracketViewSet(viewsets.ModelViewSet):
    serializer_class = BracketSerializer
    permission_classes = [LanAccess]
    queryset = Bracket.objects.select_related("weight_category", "age_group")

    def create(self, request, *args, **kwargs):
        """Create a category bracket on demand (or reuse the existing one)."""
        tournament = _tournament()
        category_id = request.data.get("weight_category")
        category = (
            WeightCategory.objects.filter(pk=category_id).first()
            if category_id
            else None
        )
        if category is None:
            return Response(
                {"error": "Укажите существующую весовую категорию"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bracket, _ = Bracket.objects.get_or_create(
            tournament=tournament,
            weight_category=category,
            defaults={
                "name": f"Сетка · {category.name}",
                "age_group": category.age_group,
                "system": tournament.system,
            },
        )
    @action(detail=False, methods=["post"])
    def setup(self, request):
        """Create brackets for every non-empty category in one call."""
        tournament = _tournament()
        created = []
        for category in WeightCategory.objects.filter(tournament=tournament):
            if not _eligible(category).exists():
                continue
            bracket, made = Bracket.objects.get_or_create(
                tournament=tournament,
                weight_category=category,
                defaults={
                    "name": f"Сетка · {category.name}",
                    "age_group": category.age_group,
                    "system": tournament.system,
                },
            )
            if made:
                created.append(bracket.id)
        return Response({"created": created, "total": Bracket.objects.count()})

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, pk=None):
        """Regenerate the bracket from a strategy without saving it."""
        bracket = self.get_object()
        strategy = request.data.get("strategy", "mixed")
        if strategy not in STRATEGIES:
            return Response(
                {"error": f"Стратегия должна быть одной из: {', '.join(STRATEGIES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        athletes = list(_eligible(bracket.weight_category))
        structure = build_bracket(athletes, strategy, bracket.system)
        structure["athletes"] = [
            {"id": athlete.pk, "name": athlete.short_name} for athlete in athletes
        ]
        return Response(structure)

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """Persist the drawn bracket and materialise its first-round bouts."""
        bracket = self.get_object()
        strategy = request.data.get("strategy", "mixed")
        athletes = list(_eligible(bracket.weight_category))
        if len(athletes) < 2:
            return Response(
                {"error": "Недостаточно участников для жеребьёвки"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        structure = build_bracket(athletes, strategy, bracket.system)
        bracket.seed_order = strategy
        bracket.data = json.dumps(structure, ensure_ascii=False)
        bracket.size = structure["size"]
        bracket.is_approved = False
        bracket.save()
        bouts = generate_bouts(bracket)
        live.broadcast(
            {"type": "draw.completed", "bracket": bracket.pk, "bouts": bouts}
        )
        return Response(
            {"bracket": bracket.pk, "bouts": bouts, "size": structure["size"]}
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        bracket = self.get_object()
        bracket.is_approved = True
        bracket.save(update_fields=["is_approved", "updated_at"])
        return Response({"approved": True, "bracket": bracket.pk})


class MatViewSet(viewsets.ModelViewSet):
    serializer_class = MatSerializer
    permission_classes = [LanAccess]
    queryset = Mat.objects.all()

    @action(detail=False, methods=["post"])
    def schedule(self, request):
        """Distribute ready bouts across mats, round-robin, avoiding idle mats.

        Bouts are spread so neighbouring mats never run the same category twice
        in a row — this keeps rest periods fair and prevents one category from
        stalling behind another.
        """
        tournament = _tournament()
        mats = list(Mat.objects.filter(tournament=tournament).order_by("number"))
        if not mats:
            return Response(
                {"error": "Не задано ни одного ковра"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bouts = list(
            Bout.objects.filter(tournament=tournament, round_no=1)
            .select_related("bracket__weight_category")
            .order_by("bracket__weight_category__order", "order_in_mat", "id")
        )
        if not bouts:
            return Response({"scheduled": 0, "message": "Схваток пока нет"})

        counters = {mat.pk: 0 for mat in mats}
        mat_index = 0
        last_category = {}
        for bout in bouts:
            chosen = mats[mat_index % len(mats)]
            category = bout.bracket.weight_category_id if bout.bracket_id else None
            # Avoid placing the same category on the same mat back-to-back.
            if last_category.get(chosen.pk) == category and len(mats) > 1:
                chosen = mats[(mat_index + 1) % len(mats)]
            counters[chosen.pk] += 1
            bout.mat = chosen
            bout.order_in_mat = counters[chosen.pk]
            if bout.participant_a and bout.participant_b:
                bout.status = BoutStatus.READY
            bout.save(update_fields=["mat", "order_in_mat", "status", "updated_at"])
            last_category[chosen.pk] = category
            mat_index += 1

        live.broadcast({"type": "schedule.updated", "bouts": len(bouts)})
        return Response({"scheduled": len(bouts)})


class BoutViewSet(viewsets.ModelViewSet):
    serializer_class = BoutSerializer
    permission_classes = [LanAccess]
    queryset = Bout.objects.select_related(
        "participant_a", "participant_b", "mat", "winner", "bracket__weight_category"
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        mat = self.request.query_params.get("mat")
        status_filter = self.request.query_params.get("status")
        if mat:
            queryset = queryset.filter(mat_id=mat)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def list(self, request, *args, **kwargs):
        program = request.query_params.get("program")
        if program:
            bouts = self.get_queryset().order_by("mat__number", "order_in_mat")[:200]
            duration = None
            try:
                duration = _tournament().bout_duration
            except Exception:  # pragma: no cover
                duration = None
            return Response(
                [
                    {
                        "id": bout.pk,
                        "mat": bout.mat.number if bout.mat_id else None,
                        "order": bout.order_in_mat,
                        "round_no": bout.round_no,
                        "a": bout.label("A"),
                        "b": bout.label("B"),
                        "status": bout.status,
                        "score_a": bout.score_a,
                        "score_b": bout.score_b,
                        "warnings_a": bout.warnings_a,
                        "warnings_b": bout.warnings_b,
                        "winner_side": bout.winner_side,
                        "result_text": bout.result_text,
                        "category": (
                            bout.bracket.weight_category.name
                            if bout.bracket_id and bout.bracket.weight_category_id
                            else ""
                        ),
                        "started_at": bout.started_at.isoformat() if bout.started_at else None,
                        "finished_at": bout.finished_at.isoformat() if bout.finished_at else None,
                        "duration": duration,
                    }
                    for bout in bouts
                ]
            )
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        bout = self.get_object()
        from .services import start_bout

        return Response(start_bout(bout))

    @action(detail=True, methods=["post"])
    def score(self, request, pk=None):
        bout = self.get_object()
        side = request.data.get("side", "").upper()
        value = request.data.get("value")
        if side not in ("A", "B"):
            return Response(
                {"error": "Укажите side = A или B"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(value, (int, float)) or int(value) <= 0:
            return Response(
                {"error": "value должен быть положительным числом"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .services import add_score

        return Response(add_score(bout, side, int(value)))

    @action(detail=True, methods=["post"])
    def warning(self, request, pk=None):
        bout = self.get_object()
        side = request.data.get("side", "").upper()
        if side not in ("A", "B"):
            return Response(
                {"error": "Укажите side = A или B"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .services import add_warning

        return Response(add_warning(bout, side))

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        bout = self.get_object()
        winner_side = request.data.get("winner_side", "").upper()
        result_text = request.data.get("result_text", "")
        from .services import finish_bout

        return Response(finish_bout(bout, winner_side, result_text))

