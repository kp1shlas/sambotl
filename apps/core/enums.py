"""Enumerations shared between the tournament config and the competition models."""
from django.db import models


class TournamentSystem(models.TextChoices):
    """Draw/bracket system selected when the tournament is created."""

    OLYMPIC = "olympic", "Олимпийская (с утешительными схватками)"
    SIX_ERRORS = "six_errors", "До 6 ошибок"


class Audience(models.TextChoices):
    ADULTS = "adults", "Взрослые"
    CHILDREN = "children", "Дети"
    MIXED = "mixed", "Смешанный"


class StageKind(models.TextChoices):
    """Lifecycle of an event; the admin dashboard shows the current stage."""

    SETUP = "setup", "Настройка"
    REGISTRATION = "registration", "Регистрация (импорт участников)"
    WEIGHING = "weighing", "Взвешивание"
    DRAW = "draw", "Жеребьёвка"
    MAT_ASSIGNMENT = "mat_assignment", "Распределение по коврам"
    COMPETITION = "competition", "Соревнование"
    FINISHED = "finished", "Завершён"


class StageStatus(models.TextChoices):
    PENDING = "pending", "Не начат"
    IN_PROGRESS = "in_progress", "Идёт"
    DONE = "done", "Завершён"


class Gender(models.TextChoices):
    MALE = "M", "Мужской"
    FEMALE = "F", "Женский"
    MIXED = "X", "Смешанный"


class ParticipantStatus(models.TextChoices):
    REGISTERED = "registered", "Зарегистрирован"
    WEIGHED = "weighed", "Взвешен"
    WEIGH_FAILED = "failed", "Не прошёл взвешивание"
    WITHDRAWN = "withdrawn", "Снят"


class BoutStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    READY = "ready", "Готова"
    ON_MAT = "on_mat", "На ковре"
    FINISHED = "finished", "Завершена"
    CANCELLED = "cancelled", "Отменена"
