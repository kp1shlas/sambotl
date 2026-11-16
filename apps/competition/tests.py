"""Tests: draw engine, bracket generation, mat scheduling."""
import json

from django.test import TestCase

from apps.competition.draw import (
    build_bracket,
    build_order,
    next_power_of_two,
)
from apps.competition.models import Bout, Bracket
from apps.core.enums import Gender, ParticipantStatus
from apps.participants.models import Participant
from apps.tournaments.models import Tournament


class NextPowerOfTwoTests(TestCase):
    def test_basics(self):
        self.assertEqual(next_power_of_two(1), 2)
        self.assertEqual(next_power_of_two(5), 8)
        self.assertEqual(next_power_of_two(8), 8)
        self.assertEqual(next_power_of_two(9), 16)


class BuildOrderTests(TestCase):
    def test_random_has_byes(self):
        players = [1, 2, 3, 4, 5, 6]
        slots = build_order(players, "random")
        self.assertIn(None, slots)
        self.assertEqual(len(slots), next_power_of_two(6))

    def test_seeded_opposite_ends(self):
        players = [1, 2, 3, 4, 5, 6, 7, 8]
        slots = build_order(players, "seeded")
        self.assertEqual(slots[0], 1)
        self.assertEqual(slots[-1], 2)


class BuildBracketTests(TestCase):
    def test_structure_shape(self):
        structure = build_bracket(["A", "B", "C", "D", "E", "F"], strategy="mixed")
        self.assertEqual(structure["size"], 8)
        self.assertEqual(len(structure["rounds"]), 3)
        self.assertEqual(len(structure["rounds"][0]), 4)
        self.assertGreater(structure["byes"], 0)


class DrawIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from decimal import Decimal as D

        from apps.competition.models import AgeGroup, Mat, WeightCategory

        cls.tournament = Tournament.objects.create(
            name="Test Draw", system="olympic", audience="adults", mats_count=3,
        )
        cls.age_group = AgeGroup.objects.create(
            tournament=cls.tournament, name="Взрослые", gender=Gender.MALE, order=0,
        )
        cls.weight_category = WeightCategory.objects.create(
            tournament=cls.tournament, age_group=cls.age_group,
            name="до 79 кг", gender=Gender.MALE, weight_from=D("71"),
            weight_to=D("79"), order=0,
        )
        for i in range(1, 4):
            Mat.objects.create(tournament=cls.tournament, number=i)
        for last in ("Ааров", "Беков", "Винтов", "Гаев", "Денов", "Ежов"):
            Participant.objects.create(
                tournament=cls.tournament, last_name=last, first_name="Иван",
                weight_category=cls.weight_category, status=ParticipantStatus.WEIGHED,
            )

    def setUp(self):
        from rest_framework.test import APIClient

        self.client = APIClient()
        self.tournament.set_password("draw123")
        self.tournament.save()
        self.client.credentials(HTTP_AUTHORIZATION="Token draw123")

    def test_full_draw_pipeline(self):
        from apps.competition.draw import build_bracket, generate_bouts

        bracket = Bracket.objects.create(
            tournament=self.tournament,
            weight_category=self.weight_category,
            name="Сетка 79 кг",
            system=self.tournament.system,
        )
        athletes = list(Participant.objects.filter(
            weight_category=self.weight_category,
            status=ParticipantStatus.WEIGHED,
        ))
        structure = build_bracket(athletes, "mixed")
        bracket.data = json.dumps(structure, ensure_ascii=False)
        bracket.seed_order = "mixed"
        bracket.size = structure["size"]
        bracket.save()

        self.assertEqual(bracket.size, 8)
        bouts = generate_bouts(bracket)
        self.assertGreater(bouts, 0)
        self.assertLessEqual(bouts, 4)

    def test_draw_api_preview(self):
        bracket = Bracket.objects.create(
            tournament=self.tournament,
            weight_category=self.weight_category,
            name="Сетка 79 кг",
            system=self.tournament.system,
        )
        response = self.client.post(
            f"/api/brackets/{bracket.pk}/preview/",
            {"strategy": "seeded"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        structure = response.json()
        self.assertIn("rounds", structure)
        self.assertIn("athletes", structure)
        self.assertEqual(len(structure["athletes"]), 6)

    def test_mat_scheduling_distributes_bouts(self):
        from decimal import Decimal as D

        from apps.competition import models as cm
        from apps.competition.draw import build_bracket, generate_bouts
        from rest_framework.test import APIClient

        wc2 = cm.WeightCategory.objects.create(
            tournament=self.tournament, age_group=self.age_group,
            name="до 88 кг", gender=Gender.MALE, weight_from=D("79"),
            weight_to=D("88"), order=1,
        )
        for name in ("Килов", "Ломов", "Минов"):
            Participant.objects.create(
                tournament=self.tournament, last_name=name, first_name="А",
                weight_category=wc2, status=ParticipantStatus.WEIGHED,
            )

        for name, wc in [("Сетка A", self.weight_category), ("Сетка B", wc2)]:
            bracket = Bracket.objects.create(
                tournament=self.tournament, weight_category=wc,
                name=name, system="olympic",
            )
            athletes = list(Participant.objects.filter(weight_category=wc))
            structure = build_bracket(athletes, "random")
            bracket.data = json.dumps(structure, ensure_ascii=False)
            bracket.size = structure["size"]
            bracket.save()
            generate_bouts(bracket)

        client = self.client
        response = client.post("/api/mats/schedule/", format="json")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()["scheduled"], 0)
        self.assertEqual(Bout.objects.filter(mat__isnull=True).count(), 0)

    def test_regenerate_does_not_duplicate_bouts(self):
        """Повторная жеребьёвка не должна плодить дубли схваток."""
        from apps.competition.draw import build_bracket, generate_bouts
        from apps.competition.models import Bout

        bracket = Bracket.objects.create(
            tournament=self.tournament,
            weight_category=self.weight_category,
            name="Сетка повтора",
            system="olympic",
        )
        athletes = list(Participant.objects.filter(
            weight_category=self.weight_category,
            status=ParticipantStatus.WEIGHED,
        ))
        structure = build_bracket(athletes, "random")
        bracket.data = json.dumps(structure, ensure_ascii=False)
        bracket.size = structure["size"]
        bracket.save()

        first = generate_bouts(bracket)
        # Mark them scheduled (ready) — this used to leave stale duplicates.
        Bout.objects.filter(bracket=bracket).update(status="ready")
        second = generate_bouts(bracket)

        self.assertEqual(first, second)
        self.assertEqual(Bout.objects.filter(bracket=bracket).count(), second)

    def test_bout_control_lifecycle(self):
        """Управление схваткой: start → score → finish через API."""
        from apps.competition.models import Bout, Bracket
        from apps.competition.draw import build_bracket, generate_bouts

        bracket = Bracket.objects.create(
            tournament=self.tournament,
            weight_category=self.weight_category,
            name="Сетка управления",
            system="olympic",
        )
        athletes = list(Participant.objects.filter(
            weight_category=self.weight_category,
            status=ParticipantStatus.WEIGHED,
        ))
        structure = build_bracket(athletes, "random")
        bracket.data = json.dumps(structure, ensure_ascii=False)
        bracket.size = structure["size"]
        bracket.save()
        generate_bouts(bracket)

        bout = Bout.objects.filter(
            bracket=bracket, participant_a__isnull=False, participant_b__isnull=False
        ).first()
        self.assertIsNotNone(bout)

        # start
        response = self.client.post(f"/api/bouts/{bout.pk}/start/", format="json")
        self.assertEqual(response.status_code, 200)
        bout.refresh_from_db()
        self.assertEqual(bout.status, "on_mat")

        # score A +4
        response = self.client.post(
            f"/api/bouts/{bout.pk}/score/", {"side": "A", "value": 4}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        bout.refresh_from_db()
        self.assertEqual(bout.score_a, 4)

        # warning B
        self.client.post(
            f"/api/bouts/{bout.pk}/warning/", {"side": "B"}, format="json"
        )
        bout.refresh_from_db()
        self.assertEqual(bout.warnings_b, 1)

        # finish — A wins
        response = self.client.post(
            f"/api/bouts/{bout.pk}/finish/",
            {"winner_side": "A", "result_text": "Чистая победа"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        bout.refresh_from_db()
        self.assertEqual(bout.status, "finished")
        self.assertEqual(bout.winner_side, "A")
        self.assertEqual(bout.winner_id, bout.participant_a_id)