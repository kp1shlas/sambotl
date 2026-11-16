"""Competition entities: categories, mats, referees, brackets and bouts."""
from django.db import models

from apps.core.enums import (
    BoutStatus,
    Gender,
    ParticipantStatus,
    TournamentSystem,
)
from apps.core.models import TimeStampedModel


class AgeGroup(TimeStampedModel):
    """Age group / weight band subdivision (adults, juniors, children)."""

    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE,
        related_name="age_groups", verbose_name="Турнир",
    )
    name = models.CharField("Название", max_length=120)
    gender = models.CharField(
        "Пол", max_length=1, choices=Gender.choices, blank=True,
        help_text="Пусто = для всех",
    )
    birth_year_from = models.PositiveSmallIntegerField("Год рождения от", null=True, blank=True)
    birth_year_to = models.PositiveSmallIntegerField("Год рождения до", null=True, blank=True)
    is_children = models.BooleanField("Детская группа", default=False)
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Возрастная группа"
        verbose_name_plural = "Возрастные группы"
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name


class WeightCategory(TimeStampedModel):
    """A weight class such as «до 90 кг» or «90+ кг».

    ``weight_from`` is the lower bound (``None`` = from zero) and ``weight_to``
    is the upper bound (``None`` = open / heaviest class). This is what the
    Excel import uses both for parsing «до 90» and for auto-detection by weight.
    """

    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE,
        related_name="weight_categories", verbose_name="Турнир",
    )
    age_group = models.ForeignKey(
        AgeGroup, on_delete=models.CASCADE, null=True, blank=True,
        related_name="weight_categories", verbose_name="Возрастная группа",
    )
    name = models.CharField("Название", max_length=80)
    gender = models.CharField("Пол", max_length=1, choices=Gender.choices, blank=True)
    weight_from = models.DecimalField(
        "Вес от, кг", max_digits=6, decimal_places=2, null=True, blank=True
    )
    weight_to = models.DecimalField(
        "Вес до, кг", max_digits=6, decimal_places=2, null=True, blank=True
    )
    is_open = models.BooleanField(
        "Открытая (самая тяжёлая)", default=False,
        help_text="Например, «90+ кг»",
    )
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Весовая категория"
        verbose_name_plural = "Весовые категории"
        ordering = ["age_group__order", "order", "weight_to"]

    def __str__(self) -> str:
        prefix = f"{self.age_group.name} · " if self.age_group_id else ""
        return f"{prefix}{self.name}"


class Mat(TimeStampedModel):
    """A wrestling mat (kovyör) — normally 3-4 per tournament."""

    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE,
        related_name="mats", verbose_name="Турнир",
    )
    number = models.PositiveSmallIntegerField("Номер ковра")
    name = models.CharField("Название", max_length=80, blank=True)
    location = models.CharField("Расположение", max_length=120, blank=True)

    class Meta:
        verbose_name = "Ковёр"
        verbose_name_plural = "Ковры"
        unique_together = ("tournament", "number")
        ordering = ["number"]

    def __str__(self) -> str:
        return self.name or f"Ковёр {self.number}"


class Referee(TimeStampedModel):
    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE,
        related_name="referees", verbose_name="Турнир",
    )
    full_name = models.CharField("ФИО судьи", max_length=200)
    category = models.CharField("Судейская категория", max_length=80, blank=True)
    access_code = models.CharField("Код доступа", max_length=40, blank=True)

    class Meta:
        verbose_name = "Судья"
        verbose_name_plural = "Судьи"
        ordering = ["full_name"]

    def __str__(self) -> str:
        return self.full_name


class Bracket(TimeStampedModel):
    """A draw / bracket for one category.

    ``seed_order`` and ``data`` store JSON: the order of seeded participants and
    the resolved bracket structure (pairs, byes, losers bracket). This keeps the
    skeleton flexible for both the Olympic system (with repechage) and the
    «до 6 ошибок» (round-robin style) system.
    """

    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE,
        related_name="brackets", verbose_name="Турнир",
    )
    weight_category = models.ForeignKey(
        WeightCategory, on_delete=models.CASCADE, null=True, blank=True,
        related_name="brackets", verbose_name="Весовая категория",
    )
    age_group = models.ForeignKey(
        AgeGroup, on_delete=models.CASCADE, null=True, blank=True,
        related_name="brackets", verbose_name="Возрастная группа",
    )
    name = models.CharField("Название сетки", max_length=120, blank=True)
    system = models.CharField(
        "Система", max_length=20, choices=TournamentSystem.choices,
        default=TournamentSystem.OLYMPIC,
    )
    size = models.PositiveSmallIntegerField("Размер сетки", default=0)
    seed_order = models.TextField("Порядок посева (JSON)", blank=True)
    data = models.TextField("Структура сетки (JSON)", blank=True)
    is_approved = models.BooleanField("Утверждена", default=False)

    class Meta:
        verbose_name = "Сетка"
        verbose_name_plural = "Сетки"
        ordering = ["weight_category__order", "id"]

    def __str__(self) -> str:
        if self.name:
            return self.name
        return str(self.weight_category or self.age_group or f"Сетка {self.id}")


class Bout(TimeStampedModel):
    """A single bout scheduled on a mat.

    Until the draw resolves a pair, ``placeholder_a``/``placeholder_b`` carry
    text like «Победитель схватки 12» so the schedule screen can still display
    the upcoming bout.
    """

    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE,
        related_name="bouts", verbose_name="Турнир",
    )
    bracket = models.ForeignKey(
        Bracket, on_delete=models.CASCADE, null=True, blank=True,
        related_name="bouts", verbose_name="Сетка",
    )
    mat = models.ForeignKey(
        Mat, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bouts", verbose_name="Ковёр",
    )
    round_no = models.PositiveSmallIntegerField("Круг", default=1)
    order_in_mat = models.PositiveSmallIntegerField("Порядок на ковре", default=0)

    participant_a = models.ForeignKey(
        "participants.Participant", on_delete=models.SET_NULL, null=True,
        blank=True, related_name="+", verbose_name="Участник A",
    )
    participant_b = models.ForeignKey(
        "participants.Participant", on_delete=models.SET_NULL, null=True,
        blank=True, related_name="+", verbose_name="Участник B",
    )
    placeholder_a = models.CharField("Метка A", max_length=120, blank=True)
    placeholder_b = models.CharField("Метка B", max_length=120, blank=True)

    status = models.CharField(
        "Статус", max_length=20, choices=BoutStatus.choices,
        default=BoutStatus.PENDING,
    )
    score_a = models.PositiveSmallIntegerField("Очки A", default=0)
    score_b = models.PositiveSmallIntegerField("Очки B", default=0)
    warnings_a = models.PositiveSmallIntegerField("Замечания A", default=0)
    warnings_b = models.PositiveSmallIntegerField("Замечания B", default=0)

    winner = models.ForeignKey(
        "participants.Participant", on_delete=models.SET_NULL, null=True,
        blank=True, related_name="+", verbose_name="Победитель",
    )
    winner_side = models.CharField("Сторона победителя", max_length=1, blank=True)
    result_text = models.CharField("Результат", max_length=120, blank=True)

    scheduled_at = models.DateTimeField("Запланирована", null=True, blank=True)
    started_at = models.DateTimeField("Начата", null=True, blank=True)
    finished_at = models.DateTimeField("Завершена", null=True, blank=True)

    class Meta:
        verbose_name = "Схватка"
        verbose_name_plural = "Схватки"
        ordering = ["mat__number", "order_in_mat", "id"]
        indexes = [
            models.Index(fields=["tournament", "status"]),
            models.Index(fields=["tournament", "mat", "order_in_mat"]),
        ]

    def __str__(self) -> str:
        a = self.participant_a or self.placeholder_a or "—"
        b = self.participant_b or self.placeholder_b or "—"
        return f"{a} vs {b}"

    def label(self, side: str) -> str:
        """Display label for one side (participant or placeholder)."""
        participant = self.participant_a if side == "A" else self.participant_b
        placeholder = self.placeholder_a if side == "A" else self.placeholder_b
        if participant:
            return participant.short_name
        return placeholder or "—"


class BoutEvent(TimeStampedModel):
    """Audit log of scoring / penalties for a bout (reports & dispute handling)."""

    class Kind(models.TextChoices):
        START = "start", "Начало"
        SCORE = "score", "Оценка"
        WARNING = "warning", "Замечание"
        PENALTY = "penalty", "Штраф"
        END = "end", "Конец"
        RESULT = "result", "Итог"

    bout = models.ForeignKey(
        Bout, on_delete=models.CASCADE, related_name="events", verbose_name="Схватка"
    )
    kind = models.CharField("Тип", max_length=20, choices=Kind.choices)
    side = models.CharField("Сторона", max_length=1, blank=True)
    value = models.CharField("Значение", max_length=120, blank=True)
    note = models.CharField("Примечание", max_length=255, blank=True)

    class Meta:
        verbose_name = "Событие схватки"
        verbose_name_plural = "События схваток"
        ordering = ["bout_id", "created_at"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.side} {self.value}".strip()


