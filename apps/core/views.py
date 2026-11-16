"""Report download endpoints (Excel / Word)."""
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes

from apps.competition.models import Bracket
from apps.core import reports
from apps.core.auth import LanAccess
from apps.tournaments.models import Tournament

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _tournament() -> Tournament:
    return Tournament.objects.order_by("id").first()


def _file_response(content: bytes, filename: str, content_type: str) -> HttpResponse:
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
@permission_classes([LanAccess])
def weighing_report(request):
    """Протокол взвешивания (Excel)."""
    tournament = _tournament()
    if tournament is None:
        return HttpResponse(status=404)
    content = reports.weighing_protocol_xlsx(tournament)
    return _file_response(content, f"взвешивание-{tournament.name}.xlsx", XLSX)


@api_view(["GET"])
@permission_classes([LanAccess])
def bracket_report(request, bracket_id: int):
    """Сетка категории (Excel)."""
    bracket = Bracket.objects.filter(pk=bracket_id).first()
    if bracket is None:
        return HttpResponse(status=404)
    content = reports.bracket_xlsx(bracket)
    return _file_response(content, f"сетка-{bracket.pk}.xlsx", XLSX)


@api_view(["GET"])
@permission_classes([LanAccess])
def results_report(request):
    """Итоговый протокол (Word)."""
    tournament = _tournament()
    if tournament is None:
        return HttpResponse(status=404)
    content = reports.results_docx(tournament)
    return _file_response(content, f"итоги-{tournament.name}.docx", DOCX)

