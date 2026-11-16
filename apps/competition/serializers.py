"""Serializers for the competition app: brackets, mats, bouts."""
from rest_framework import serializers

from .models import Bout, Bracket, Mat


class WeightCategoryRefSerializer(serializers.RelatedField):
    """Simply render the category name string."""

    def to_representation(self, value):
        return str(value)


class BracketSerializer(serializers.ModelSerializer):
    weight_category = WeightCategoryRefSerializer(read_only=True)
    age_group_name = serializers.CharField(source="age_group.name", default="", read_only=True)
    athletes_count = serializers.SerializerMethodField()

    class Meta:
        model = Bracket
        fields = [
            "id",
            "name",
            "weight_category",
            "age_group_name",
            "system",
            "size",
            "is_approved",
            "athletes_count",
        ]

    def get_athletes_count(self, obj) -> int:
        weight_category = obj.weight_category
        if not weight_category:
            return 0
        return weight_category.participants.count()


class MatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mat
        fields = ["id", "number", "name", "location"]


class BoutSerializer(serializers.ModelSerializer):
    mat_number = serializers.IntegerField(source="mat.number", read_only=True)
    bracket_name = serializers.CharField(
        source="bracket.weight_category.name", default="", read_only=True
    )

    class Meta:
        model = Bout
        fields = [
            "id",
            "mat",
            "mat_number",
            "bracket",
            "bracket_name",
            "round_no",
            "order_in_mat",
            "participant_a",
            "participant_b",
            "placeholder_a",
            "placeholder_b",
            "status",
            "score_a",
            "score_b",
            "warnings_a",
            "warnings_b",
            "winner",
            "winner_side",
            "result_text",
            "started_at",
            "finished_at",
        ]
        read_only_fields = ("started_at", "finished_at")