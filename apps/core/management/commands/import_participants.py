"""Import participants from an .xlsx file into the active tournament.

Usage::

    python manage.py import_participants data/samples/participants_sample.xlsx
    python manage.py import_participants file.xlsx --dry-run
"""
from django.core.management.base import BaseCommand, CommandError

from apps.core.excel import import_participants
from apps.tournaments.models import Tournament


class Command(BaseCommand):
    help = "Импортировать участников из Excel в активный турнир"

    def add_arguments(self, parser):
        parser.add_argument("path", help="Путь к файлу .xlsx")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только проверить файл, ничего не записывать",
        )
        parser.add_argument(
            "--tournament-id",
            type=int,
            default=None,
            help="ID турнира (по умолчанию — первый/единственный в базе)",
        )

    def handle(self, *args, **options):
        tournament = None
        if options["tournament_id"]:
            tournament = Tournament.objects.filter(pk=options["tournament_id"]).first()
        if tournament is None:
            tournament = Tournament.objects.order_by("id").first()
        if tournament is None:
            raise CommandError(
                "В текущей базе нет ни одного турнира. "
                "Сначала выполните: new_tournament <название>"
            )

        result = import_participants(
            tournament, options["path"], dry_run=options["dry_run"]
        )

        prefix = "[ПРОВЕРКА] " if options["dry_run"] else ""
        self.stdout.write(f"{prefix}Турнир: {tournament.name}")
        self.stdout.write(
            "Распознаны колонки: "
            + ", ".join(f"{label}→{field}" for label, field in result.recognised_columns.items())
        )
        if result.missing_columns:
            self.stderr.write(
                "ОТСУТСТВУЮТ обязательные колонки: " + ", ".join(result.missing_columns)
            )
        label = "Готово к импорту" if options["dry_run"] else "Импортировано"
        self.stdout.write(f"{label}: {result.created}")
        self.stdout.write(f"Пропущено: {result.skipped}")
        for warning in result.warnings:
            self.stdout.write(self.style.WARNING(f"  ! {warning}"))
        for error in result.errors:
            self.stderr.write(self.style.ERROR(f"  x {error}"))
