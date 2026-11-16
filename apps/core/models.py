from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base with creation/update timestamps shared by all models."""

    created_at = models.DateTimeField("Создано", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        abstract = True
