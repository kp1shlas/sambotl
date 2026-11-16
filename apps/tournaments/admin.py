"""Unfold admin for tournaments and stages."""
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Stage, Tournament


class StageInline(TabularInline):
    model = Stage
    extra = 0
    fields = ("kind", "status", "started_at", "finished_at", "note")
    ordering = ("kind",)


@admin.register(Tournament)
class TournamentAdmin(ModelAdmin):
    list_display = (
        "name",
        "association",
        "system",
        "audience",
        "mats_count",
        "current_stage",
        "date_start",
        "weighing_progress",
    )
    list_filter = ("system", "audience", "current_stage", "is_archived")
    search_fields = ("name", "association", "location")
    inlines = (StageInline,)
    readonly_fields = ("created_at", "updated_at", "weighing_progress")
    fieldsets = (
        (
            "Общая информация",
            {
                "fields": (
                    "name",
                    "association",
                    "location",
                    ("date_start", "date_end"),
                )
            },
        ),
        (
            "Правила и этапы",
            {
                "fields": (
                    ("system", "audience"),
                    ("mats_count", "current_stage"),
                    "weighing_progress",
                )
            },
        ),
        (
            "Регламент времени",
            {
                "fields": (
                    ("bout_duration_adults", "bout_duration_children"),
                    ("break_duration", "overtime_duration"),
                )
            },
        ),
        (
            "Брендинг (экраны и расписание)",
            {"fields": ("logo_tournament", "logo_association", "logo_sponsor")},
        ),
        ("Доступ", {"fields": ("access_password", "is_archived", "notes")}),
        ("Служебное", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Взвешивание")
    def weighing_progress(self, obj):
        """Live «прошло / всего» counter shown on the admin dashboard."""
        total = obj.participants.count()
        if not total:
            return "—"
        passed = obj.weigh_ins.filter(passed=True).count()
        return f"{passed} / {total}"

    def save_model(self, request, obj, form, change):
        if "access_password" in form.data and form.data.get("access_password"):
            obj.set_password(form.data["access_password"])
        super().save_model(request, obj, form, change)


@admin.register(Stage)
class StageAdmin(ModelAdmin):
    list_display = ("tournament", "kind", "status", "started_at", "finished_at")
    list_filter = ("kind", "status", "tournament")
    search_fields = ("tournament__name", "note")
    autocomplete_fields = ("tournament",)
