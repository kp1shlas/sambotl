"""End-to-end API smoke test against the *active* tournament database.

Run:  python scripts/smoke_api.py   (password from SAMBO_PASSWORD, default 1234)
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from rest_framework.test import APIClient  # noqa: E402

from apps.tournaments.models import Tournament  # noqa: E402


def main() -> int:
    tournament = Tournament.objects.order_by("id").first()
    if tournament is None:
        print("Нет турнира. Создайте: manage.py new_tournament \"Название\" --activate")
        return 1

    password = os.environ.get("SAMBO_PASSWORD", "1234")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {password}")

    def show(label: str, response):
        ok = 200 <= response.status_code < 300
        print(f"{'OK ' if ok else 'ERR'} {label}: {response.status_code}")
        return response

    print(f"Турнир: {tournament.name}")

    show("health", client.get("/api/health/"))

    participants = show("GET /api/participants/", client.get("/api/participants/"))
    if participants.status_code == 200:
        print(f"    участников: {len(participants.json())}")

    setup = show("POST /api/brackets/setup/", client.post("/api/brackets/setup/"))
    brackets = client.get("/api/brackets/")
    show("GET /api/brackets/", brackets)
    items = brackets.json() if brackets.status_code == 200 else []
    if isinstance(items, dict):
        items = items.get("results", [])
    ready = [item for item in items if item.get("athletes_count", 0) >= 2]
    if not ready:
        print("Нет категорий с 2+ участниками для жеребьёвки.")
        return 0

    bracket_id = ready[0]["id"]
    print(f"    сеток всего: {len(items)}, подходящая: #{bracket_id} "
          f"({ready[0]['weight_category']}, участников {ready[0]['athletes_count']})")
    preview = show(
        f"POST /api/brackets/{bracket_id}/preview/",
        client.post(
            f"/api/brackets/{bracket_id}/preview/",
            {"strategy": "mixed"},
            format="json",
        ),
    )
    if preview.status_code == 200:
        data = preview.json()
        print(f"    размер сетки: {data['size']}, бай-мест: {data['byes']}")

    generate = show(
        f"POST /api/brackets/{bracket_id}/generate/",
        client.post(
            f"/api/brackets/{bracket_id}/generate/",
            {"strategy": "mixed"},
            format="json",
        ),
    )
    if generate.status_code == 200:
        print(f"    создано схваток: {generate.json()['bouts']}")

    schedule = show("POST /api/mats/schedule/", client.post("/api/mats/schedule/"))
    if schedule.status_code == 200:
        print(f"    распределено по коврам: {schedule.json()['scheduled']}")

    program = show("GET /api/bouts/?program=1", client.get("/api/bouts/?program=1"))
    if program.status_code == 200:
        for row in program.json()[:6]:
            print(f"    ковёр {row['mat']}: {row['a']} vs {row['b']} [{row['status']}]")

    progress = show("GET /api/weigh-ins/progress/", client.get("/api/weigh-ins/progress/"))
    if progress.status_code == 200:
        print(f"    взвешивание: {progress.json()}")

    program2 = client.get("/api/bouts/?program=1")
    if program2.status_code == 200 and program2.json():
        first = program2.json()[0]
        print("    поля программы:", ", ".join(sorted(first.keys())))

    # Bout control: start → score → finish on the first scheduled bout.
    bouts = client.get("/api/bouts/?program=1")
    bout_list = bouts.json() if bouts.status_code == 200 else []
    if isinstance(bout_list, dict):
        bout_list = bout_list.get("results", [])
    ready = [b for b in bout_list if b.get("status") in ("ready", "on_mat")]
    if ready:
        bout_id = ready[0]["id"]
        show(f"POST /api/bouts/{bout_id}/start/", client.post(f"/api/bouts/{bout_id}/start/"))
        show(f"POST /api/bouts/{bout_id}/score/", client.post(
            f"/api/bouts/{bout_id}/score/", {"side": "A", "value": 2}, format="json"
        ))
        show(f"POST /api/bouts/{bout_id}/finish/", client.post(
            f"/api/bouts/{bout_id}/finish/", {"winner_side": "A", "result_text": "тест"}, format="json"
        ))
        check = client.get(f"/api/bouts/{bout_id}/")
        if check.status_code == 200:
            data = check.json()
            print(f"    итог: {data['score_a']}:{data['score_b']} status={data['status']} winner={data['winner_side']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
