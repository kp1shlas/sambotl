"""Athletes, clubs and the weighing stage.

ФИО is stored as three separate fields (last / first / middle name) because the
scoreboard, schedule and printed protocols render them independently.
"""
from django.db import models

from apps.core.enums import Gender, ParticipantStatus
from apps.core.models import TimeStampedModel


class Club(TimeStampedModel):
    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE, related_name="clubs",
        verbose_name="Турнир",
    )
    name = models.CharField("Название клуба", max_length=200)
    region = models.CharField("Регион / город", max_length=150, blank=True)

    class Meta:
        verbose_name = "Клуб"
        verbose_name_plural = "Клубы"
        unique_together = ("tournament", "name")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Participant(TimeStampedModel):
    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE,
        related_name="participants", verbose_name="Турнир",
    )
    last_name = models.CharField("Фамилия", max_length=120, db_index=True)
    first_name = models.CharField("Имя", max_length=120, db_index=True)
    middle_name = models.CharField("Отчество", max_length=120, blank=True)

    gender = models.CharField(
        "Пол", max_length=1, choices=Gender.choices, blank=True
    )
    birth_date = models.DateField("Дата рождения", null=True, blank=True)

    age_group = models.ForeignKey(
        "competition.AgeGroup", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="participants", verbose_name="Возрастная группа",
    )
    weight_category = models.ForeignKey(
        "competition.WeightCategory", on_delete=models.SET_NULL, null=True,
        blank=True, related_name="participants", verbose_name="Весовая категория",
    )

    club = models.ForeignKey(
        Club, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="participants", verbose_name="Клуб",
    )
    region = models.CharField("Регион", max_length=150, blank=True)
    coach = models.CharField("Тренер", max_length=200, blank=True)

    declared_category = models.CharField(
        "Заявленная категория (как в файле)", max_length=80, blank=True
    )
    declared_weight = models.DecimalField(
        "Заявленный вес, кг", max_digits=6, decimal_places=2, null=True, blank=True
    )
    current_weight = models.DecimalField(
        "Текущий вес, кг", max_digits=6, decimal_places=2, null=True, blank=True
    )
    category_auto_detected = models.BooleanField(
        "Категория определена автоматически", default=False
    )

    status = models.CharField(
        "Статус", max_length=20, choices=ParticipantStatus.choices,
        default=ParticipantStatus.REGISTERED,
    )
    bib_number = models.PositiveIntegerField(
        "Номер участника", null=True, blank=True
    )

    class Meta:
        verbose_name = "Участник"
        verbose_name_plural = "Участники"
        ordering = ["weight_category__order", "last_name", "first_name"]
        indexes = [
            models.Index(fields=["tournament", "last_name", "first_name"]),
        ]

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return " ".join(
            part for part in (self.last_name, self.first_name, self.middle_name) if part
        )

    @property
    def short_name(self) -> str:
        """«Иванов И. И.» — compact form for scoreboards."""
        initials = " ".join(
            f"{part[0]}." for part in (self.first_name, self.middle_name) if part
        )
        return f"{self.last_name} {initials}".strip()


class WeighIn(TimeStampedModel):
    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE,
        related_name="weigh_ins", verbose_name="Турнир",
    )
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="weigh_in",
        verbose_name="Участник",
    )
    declared_weight = models.DecimalField(
        "Заявленный вес, кг", max_digits=6, decimal_places=2, null=True, blank=True
    )
    current_weight = models.DecimalField(
        "Текущий вес, кг", max_digits=6, decimal_places=2, null=True, blank=True
    )
    passed = models.BooleanField("Прошёл взвешивание", default=False)
    weighed_by = models.CharField("Кто взвешивал", max_length=120, blank=True)
    weighed_at = models.DateTimeField("Время взвешивания", null=True, blank=True)
    note = models.CharField("Примечание", max_length=255, blank=True)

    class Meta:
        verbose_name = "Взвешивание"
        verbose_name_plural = "Взвешивание"
        ordering = ["-weighed_at"]

    def __str__(self) -> str:
        return f"{self.participant} — {self.current_weight or '—'} кг"
