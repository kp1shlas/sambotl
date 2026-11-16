"""List registered tournaments and mark the active one.

Usage::

    python manage.py list_tournaments
    python manage.py list_tournaments --activate moscow-cup-2026
"""
from django.core.management.base import BaseCommand, CommandError

from apps.core import registry


class Command(BaseCommand):
    help = "Показать список турниров и при необходимости переключить активный"

    def add_arguments(self, parser):
        parser.add_argument(
            "--activate", default="", help="Код турнира, который нужно сделать активным"
        )

    def handle(self, *args, **options):
        if options["activate"]:
            try:
                entry = registry.set_active(options["activate"])
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(
                self.style.SUCCESS(
                    f"Активный турнир: «{entry['name']}» ({entry['db']}). "
                    "Перезапустите сервер, чтобы он подключился к этой базе."
                )
            )
            return

        entries = registry.load_index()
        if not entries:
            self.stdout.write("Турниров пока нет. Создайте: new_tournament <название>")
            return

        active = registry.get_active() or {}
        active_slug = active.get("slug")
        for entry in entries:
            marker = " *" if entry.get("slug") == active_slug else "  "
            self.stdout.write(
                f"{marker} {entry['slug']:<24} {entry['name']} "
                f"[{entry.get('system')}/{entry.get('audience')}, "
                f"ковров: {entry.get('mats')}]"
            )
        self.stdout.write("\n * — активный турнир")
