"""Generate all reports against the active tournament and save to data/reports."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from apps.competition.models import Bracket  # noqa: E402
from apps.core import reports  # noqa: E402
from apps.tournaments.models import Tournament  # noqa: E402


def main() -> int:
    tournament = Tournament.objects.order_by("id").first()
    if tournament is None:
        print("Нет турнира")
        return 1

    target = BASE_DIR / "data" / "reports"
    target.mkdir(parents=True, exist_ok=True)

    files = {
        "weighing.xlsx": reports.weighing_protocol_xlsx(tournament),
        "results.docx": reports.results_docx(tournament),
    }
    bracket = Bracket.objects.filter(tournament=tournament).first()
    if bracket is not None:
        files["bracket.xlsx"] = reports.bracket_xlsx(bracket)

    for name, content in files.items():
        path = target / name
        path.write_bytes(content)
        print(f"{name}: {len(content)} bytes -> {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
