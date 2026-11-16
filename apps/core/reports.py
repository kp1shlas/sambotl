"""Report generation (Excel + Word) for tournament paperwork.

Reports follow the standard structure used at Sambo competitions:
  * weighing protocol (protocol взвешивания) — list of athletes with declared
    and actual weight, pass/fail;
  * category bracket (сетка категории) — the draw for one weight class;
  * final results (итоговый протокол) — finished bouts with winners and results.
"""
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

_HEADER_FILL = PatternFill("solid", fgColor="1E3A5F")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_THIN = Side(style="thin", color="999999")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _style_sheet(workbook, sheet, headers, rows):
    sheet.append(headers)
    for cell in sheet[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
    for row in rows:
        sheet.append(row)
    for row in sheet.iter_rows(min_row=1):
        for cell in row:
            cell.border = _BORDER
    for index, _ in enumerate(headers, start=1):
        width = max(
            len(str(cell.value)) if cell.value is not None else 0
            for cell in sheet[get_column_letter(index)]
        )
        sheet.column_dimensions[get_column_letter(index)].width = min(max(width + 2, 10), 40)


def weighing_protocol_xlsx(tournament) -> bytes:
    """Excel protocol of weighing."""
    from apps.participants.models import Participant, WeighIn

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Взвешивание"

    weigh_map = {
        record.participant_id: record
        for record in WeighIn.objects.filter(tournament=tournament)
    }
    participants = Participant.objects.filter(tournament=tournament).select_related(
        "club", "weight_category", "age_group"
    )

    _style_sheet(
        workbook,
        sheet,
        ["№", "ФИО", "Клуб", "Регион", "Категория", "Заявленный вес", "Текущий вес", "Результат"],
        [
            [
                index,
                participant.full_name,
                participant.club.name if participant.club_id else "",
                participant.region,
                str(participant.weight_category) if participant.weight_category_id else "",
                float(participant.declared_weight) if participant.declared_weight else "",
                float(participant.current_weight) if participant.current_weight else "",
                "прошёл" if weigh_map.get(participant.pk) and weigh_map[participant.pk].passed else (
                    "не прошёл" if weigh_map.get(participant.pk) else ""
                ),
            ]
            for index, participant in enumerate(participants, start=1)
        ],
    )

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def bracket_xlsx(bracket) -> bytes:
    """Excel table of the bracket's first-round bouts."""
    import json

    from apps.participants.models import Participant

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Сетка"

    structure = json.loads(bracket.data or "{}")
    participants = Participant.objects.in_bulk(structure.get("participants", []))

    def name(participant_id):
        athlete = participants.get(participant_id)
        return athlete.short_name if athlete else "—"

    first_round = structure.get("rounds", [[]])[0] if structure.get("rounds") else []
    rows = []
    for index, pair in enumerate(first_round, start=1):
        if pair.get("bye"):
            rows.append([index, name(pair.get("a")) or name(pair.get("b")), "bye"])
        else:
            rows.append([index, name(pair.get("a")), name(pair.get("b"))])

    _style_sheet(workbook, sheet, ["№ схватки", "Участник A", "Участник B"], rows)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def results_docx(tournament) -> bytes:
    """Word document with final results per category."""
    from apps.competition.models import Bout

    document = Document()

    title = document.add_heading(tournament.name, level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph("Итоговый протокол")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    finished = (
        Bout.objects.filter(tournament=tournament, status="finished")
        .select_related("bracket__weight_category", "winner")
        .order_by("bracket__weight_category__order", "id")
    )
    if not finished.exists():
        document.add_paragraph("Завершённых схваток пока нет.")
        output = BytesIO()
        document.save(output)
        return output.getvalue()

    current_category = None
    for bout in finished:
        category_name = (
            str(bout.bracket.weight_category) if bout.bracket_id else "—"
        )
        if category_name != current_category:
            current_category = category_name
            document.add_heading(category_name, level=1)

        winner = bout.winner.short_name if bout.winner_id else bout.winner_side
        line = document.add_paragraph()
        line.add_run(f"{bout.label('A')} — {bout.label('B')}").bold = False
        line.add_run(f"   {bout.score_a}:{bout.score_b}").bold = True
        if winner:
            line.add_run(f"   победитель: {winner}")

    output = BytesIO()
    document.save(output)
    return output.getvalue()
