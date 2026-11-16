"""Tournament configuration.

Each SQLite file holds exactly one :class:`Tournament` record that carries every
setting chosen at launch: the draw system (Olympic / up to 6 errors), the
audience (adults / children / mixed), the number of mats, timing and branding.
"""
from django.db import models

from apps.core.enums import Audience, StageKind, StageStatus, TournamentSystem
from apps.core.models import TimeStampedModel


class Tournament(TimeStampedModel):
    name = models.CharField("Название", max_length=200)
    association = models.CharField(
        "Ассоциация / федерация", max_length=200, blank=True
    )
    location = models.CharField("Место проведения", max_length=200, blank=True)
    date_start = models.DateField("Дата начала", null=True, blank=True)
    date_end = models.DateField("Дата окончания", null=True, blank=True)

    system = models.CharField(
        "Система проведения",
        max_length=20,
        choices=TournamentSystem.choices,
        default=TournamentSystem.OLYMPIC,
    )
    audience = models.CharField(
        "Аудитория",
        max_length=20,
        choices=Audience.choices,
        default=Audience.ADULTS,
    )

    mats_count = models.PositiveSmallIntegerField("Количество ковров", default=4)
    current_stage = models.CharField(
        "Текущий этап",
        max_length=20,
        choices=StageKind.choices,
        default=StageKind.SETUP,
    )

    # Timing (seconds) — adults and children follow different regulations.
    bout_duration_adults = models.PositiveIntegerField(
        "Длительность схватки, взрослые (сек)", default=300
    )
    bout_duration_children = models.PositiveIntegerField(
        "Длительность схватки, дети (сек)", default=180
    )
    break_duration = models.PositiveIntegerField(
        "Перерыв между схватками (сек)", default=30
    )
    overtime_duration = models.PositiveIntegerField(
        "Дополнительное время (сек)", default=60
    )

    # Branding — shown on scoreboards and schedule screens.
    logo_tournament = models.FileField(
        "Логотип турнира", upload_to="logos/", blank=True
    )
    logo_association = models.FileField(
        "Логотип ассоциации", upload_to="logos/", blank=True
    )
    logo_sponsor = models.FileField(
        "Логотип спонсора", upload_to="logos/", blank=True
    )

    # Shared access password for LAN client screens (stored hashed).
    access_password = models.CharField("Пароль доступа (hash)", max_length=255, blank=True)

    notes = models.TextField("Примечания", blank=True)
    is_archived = models.BooleanField("Архивный", default=False)

    class Meta:
        verbose_name = "Турнир"
        verbose_name_plural = "Турниры"
        ordering = ["-date_start", "name"]

    def __str__(self) -> str:
        return self.name

    def set_password(self, raw: str) -> None:
        from apps.core.passwords import hash_password

        self.access_password = hash_password(raw)

    def check_password(self, raw: str) -> bool:
        from apps.core.passwords import verify_password

        return verify_password(raw, self.access_password)

    @property
    def bout_duration(self) -> int:
        """Bout length that matches the tournament audience."""
        if self.audience == Audience.CHILDREN:
            return self.bout_duration_children
        return self.bout_duration_adults


class Stage(TimeStampedModel):
    """One row per workflow stage (registration, weighing, draw, ...)."""

    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name="stages",
        verbose_name="Турнир",
    )
    kind = models.CharField("Этап", max_length=20, choices=StageKind.choices)
    status = models.CharField(
        "Статус", max_length=20, choices=StageStatus.choices,
        default=StageStatus.PENDING,
    )
    started_at = models.DateTimeField("Начат", null=True, blank=True)
    finished_at = models.DateTimeField("Завершён", null=True, blank=True)
    note = models.CharField("Комментарий", max_length=255, blank=True)

    class Meta:
        verbose_name = "Этап"
        verbose_name_plural = "Этапы"
        unique_together = ("tournament", "kind")
        ordering = ["tournament", "kind"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.get_status_display()}"
