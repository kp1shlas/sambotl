"""Create a new tournament: a registry entry plus its own SQLite database.

Usage::

    python manage.py new_tournament "Кубок Москвы 2026" \\
        --system olympic --audience adults --mats 4 --password secret --activate
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.core import registry
from apps.core.enums import Audience, TournamentSystem
from apps.core.passwords import hash_password


class Command(BaseCommand):
    help = "Создать новый турнир (отдельный файл SQLite) в реестре"

    def add_arguments(self, parser):
        parser.add_argument("name", help="Название турнира")
        parser.add_argument(
            "--system",
            choices=[choice.value for choice in TournamentSystem],
            default=TournamentSystem.OLYMPIC.value,
            help="Система проведения: olympic (олимпийская) / six_errors (до 6 ошибок)",
        )
        parser.add_argument(
            "--audience",
            choices=[choice.value for choice in Audience],
            default=Audience.ADULTS.value,
            help="Аудитория: adults / children / mixed",
        )
        parser.add_argument("--mats", type=int, default=4, help="Количество ковров")
        parser.add_argument("--password", default="", help="Пароль доступа клиентов")
        parser.add_argument(
            "--slug",
            default="",
            help="Необязательный код турнира (по умолчанию из названия)",
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Сразу сделать турнир активным для сервера",
        )

    def handle(self, *args, **options):
        name = options["name"].strip()
        if not name:
            raise CommandError("Название турнира не может быть пустым")

        entry = registry.create_entry(
            name,
            system=options["system"],
            audience=options["audience"],
            mats=options["mats"],
            password_hash=hash_password(options["password"]),
            slug=options["slug"] or None,
        )

        # Point the default connection at the brand-new SQLite file *before*
        # touching the ORM, then create the schema inside that file. This is
        # what makes the "one file per tournament" model work.
        from django.db import connections

        connections.databases["default"]["NAME"] = str(registry.db_path(entry["db"]))
        connections["default"].close()

        call_command("migrate", database="default", verbosity=0, interactive=False)

        from apps.core.seed import bootstrap_tournament

        tournament = bootstrap_tournament(
            name=entry["name"],
            system=entry["system"],
            audience=entry["audience"],
            mats=entry["mats"],
            password_hash=entry["password_hash"],
        )
        self.stdout.write(
            f"  создано: ковров — {tournament.mats.count()}, "
            f"категорий — {tournament.weight_categories.count()}"
        )

        if options["activate"]:
            registry.set_active(entry["slug"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Создан турнир «{entry['name']}»\n"
                f"  код:   {entry['slug']}\n"
                f"  файл:  {entry['db']}\n"
                f"  база:  {registry.db_path(entry['db'])}\n"
                f"  система: {entry['system']} / {entry['audience']} / ковров: {entry['mats']}"
            )
        )
