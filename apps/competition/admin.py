"""Unfold admin for competition entities (categories, mats, bouts, brackets)."""
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.core import live
from apps.core.enums import BoutStatus

from .models import AgeGroup, Bout, BoutEvent, Bracket, Mat, Referee, WeightCategory


class BoutEventInline(TabularInline):
    model = BoutEvent
    extra = 0
    fields = ("kind", "side", "value", "note")
    readonly_fields = ("created_at",)


@admin.register(AgeGroup)
class AgeGroupAdmin(ModelAdmin):
    list_display = (
        "name",
        "gender",
        "birth_year_from",
        "birth_year_to",
        "is_children",
        "order",
        "categories_count",
    )
    list_filter = ("gender", "is_children")
    search_fields = ("name",)
    ordering = ("order", "name")

    @admin.display(description="Категорий")
    def categories_count(self, obj):
        return obj.weight_categories.count()


@admin.register(WeightCategory)
class WeightCategoryAdmin(ModelAdmin):
    list_display = (
        "name",
        "age_group",
        "gender",
        "weight_from",
        "weight_to",
        "is_open",
        "order",
        "athletes",
    )
    list_filter = ("age_group", "gender", "is_open")
    search_fields = ("name", "age_group__name")
    autocomplete_fields = ("age_group",)
    ordering = ("age_group__order", "order", "weight_to")

    @admin.display(description="Участников")
    def athletes(self, obj):
        return obj.participants.count()


@admin.register(Mat)
class MatAdmin(ModelAdmin):
    list_display = ("number", "name", "location", "bouts_count")
    search_fields = ("name",)
    ordering = ("number",)

    @admin.display(description="Схваток")
    def bouts_count(self, obj):
        return obj.bouts.count()


@admin.register(Referee)
class RefereeAdmin(ModelAdmin):
    list_display = ("full_name", "category", "access_code")
    search_fields = ("full_name",)


@admin.register(Bracket)
class BracketAdmin(ModelAdmin):
    list_display = (
        "name",
        "weight_category",
        "age_group",
        "system",
        "size",
        "is_approved",
    )
    list_filter = ("system", "is_approved", "weight_category")
    search_fields = ("name", "weight_category__name")
    autocomplete_fields = ("weight_category", "age_group")


@admin.register(Bout)
class BoutAdmin(ModelAdmin):
    list_display = (
        "__str__",
        "mat",
        "round_no",
        "status",
        "score_a",
        "score_b",
        "winner",
        "started_at",
    )
    list_filter = ("status", "mat", "round_no")
    search_fields = (
        "participant_a__last_name",
        "participant_b__last_name",
        "placeholder_a",
        "placeholder_b",
    )
    autocomplete_fields = ("participant_a", "participant_b", "winner", "mat", "bracket")
    inlines = (BoutEventInline,)
    list_select_related = ("participant_a", "participant_b", "winner", "mat")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status in (BoutStatus.ON_MAT, BoutStatus.FINISHED):
            live.broadcast(
                {
                    "type": "bout.updated",
                    "bout_id": obj.pk,
                    "mat": obj.mat.number if obj.mat_id else None,
                    "status": obj.status,
                    "score_a": obj.score_a,
                    "score_b": obj.score_b,
                }
            )
