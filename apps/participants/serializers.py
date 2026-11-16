"""Serializers: participants, weighing, draw preview and bout scheduling."""
from rest_framework import serializers
from apps.competition.models import Bout
from apps.participants.models import Participant, WeighIn


class ParticipantSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    short_name = serializers.CharField(read_only=True)
    category = serializers.CharField(
        source="weight_category", read_only=True
    )
    age_group = serializers.CharField(read_only=True, default="")
    club_name = serializers.CharField(source="club.name", read_only=True, default="")

    class Meta:
        model = Participant
        fields = [
            "id",
            "last_name",
            "first_name",
            "middle_name",
            "full_name",
            "short_name",
            "gender",
            "birth_date",
            "age_group",
            "category",
            "club_name",
            "region",
            "declared_weight",
            "current_weight",
            "status",
            "bib_number",
        ]


class WeighInSerializer(serializers.ModelSerializer):
    participant = ParticipantSerializer(read_only=True)
    participant_id = serializers.PrimaryKeyRelatedField(
        queryset=Participant.objects.none(), write_only=True
    )

    class Meta:
        model = WeighIn
        fields = [
            "id",
            "participant",
            "participant_id",
            "declared_weight",
            "current_weight",
            "passed",
            "weighed_by",
            "weighed_at",
            "note",
        ]
        read_only_fields = ("weighed_at",)

    def __init__(self, *args, tournament=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tournament is not None:
            self.fields["participant_id"].queryset = tournament.participants.all()