"""Unfold admin for athletes, clubs and weighing (with live progress push)."""
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.core import live
from apps.core.enums import ParticipantStatus

from .models import Club, Participant, WeighIn


class WeighInInline(TabularInline):
    model = WeighIn
    extra = 0
    fields = (
        "declared_weight",
        "current_weight",
        "passed",
        "weighed_by",
        "weighed_at",
        "note",
    )


@admin.register(Club)
class ClubAdmin(ModelAdmin):
    list_display = ("name", "region", "athletes")
    search_fields = ("name", "region")

    @admin.display(description="Участников")
    def athletes(self, obj):
        return obj.participants.count()


@admin.register(Participant)
class ParticipantAdmin(ModelAdmin):
    list_display = (
        "full_name",
        "gender",
        "birth_date",
        "age_group",
        "weight_category",
        "club",
        "declared_weight",
        "current_weight",
        "status",
    )
    list_filter = ("status", "gender", "age_group", "weight_category", "club")
    search_fields = ("last_name", "first_name", "middle_name", "club__name", "region")
    autocomplete_fields = ("age_group", "weight_category", "club")
    inlines = (WeighInInline,)
    list_select_related = ("club", "age_group", "weight_category")
    fieldsets = (
        ("ФИО", {"fields": ("last_name", "first_name", "middle_name")}),
        ("Личные данные", {"fields": (("gender", "birth_date"), "age_group")}),
        (
            "Категории и веса",
            {
                "fields": (
                    "weight_category",
                    ("declared_category", "category_auto_detected"),
                    ("declared_weight", "current_weight"),
                )
            },
        ),
        ("Клуб и тренер", {"fields": ("club", "region", "coach")}),
        ("Участие", {"fields": ("status", "bib_number", "tournament")}),
    )


@admin.register(WeighIn)
class WeighInAdmin(ModelAdmin):
    list_display = (
        "participant",
        "declared_weight",
        "current_weight",
        "passed",
        "weighed_by",
        "weighed_at",
    )
    list_filter = ("passed", "tournament")
    search_fields = ("participant__last_name", "participant__first_name")
    autocomplete_fields = ("participant", "tournament")
    list_select_related = ("participant", "tournament")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        participant = obj.participant
        if obj.current_weight is not None:
            participant.current_weight = obj.current_weight
        participant.status = (
            ParticipantStatus.WEIGHED if obj.passed else ParticipantStatus.WEIGH_FAILED
        )
        participant.save(
            update_fields=["current_weight", "status", "updated_at"]
        )
        self._broadcast_progress(obj.tournament)

    @staticmethod
    def _broadcast_progress(tournament) -> None:
        """Push the weighing progress to every connected screen in real time."""
        total = tournament.participants.count()
        passed = tournament.weigh_ins.filter(passed=True).count()
        live.broadcast(
            {"type": "weighing.progress", "total": total, "done": passed}
        )
