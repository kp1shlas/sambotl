"""Tests for core helpers: weight parsing, password hashing, slugify, reports."""
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from apps.core.enums import Gender, ParticipantStatus
from apps.core.passwords import hash_password, verify_password
from apps.core.registry import slugify
from apps.core.weight import parse_weight, pick_category
from apps.tournaments.models import Tournament


class ReportTests(TestCase):
    """Отчёты генерируют валидные xlsx/docx с данными."""

    @classmethod
    def setUpTestData(cls):
        from decimal import Decimal as D

        from apps.competition.models import AgeGroup, Bracket, WeightCategory
        from apps.participants.models import Participant

        cls.tournament = Tournament.objects.create(
            name="Test Reports", system="olympic", audience="adults", mats_count=2,
        )
        cls.age_group = AgeGroup.objects.create(
            tournament=cls.tournament, name="Взрослые", gender=Gender.MALE, order=0,
        )
        cls.weight_category = WeightCategory.objects.create(
            tournament=cls.tournament, age_group=cls.age_group,
            name="до 79 кг", gender=Gender.MALE, weight_from=D("71"),
            weight_to=D("79"), order=0,
        )
        for last in ("Ааров", "Беков"):
            Participant.objects.create(
                tournament=cls.tournament, last_name=last, first_name="Иван",
                weight_category=cls.weight_category,
                declared_weight=D("78.0"),
                current_weight=D("78.5"),
                status=ParticipantStatus.WEIGHED,
            )
        cls.bracket = Bracket.objects.create(
            tournament=cls.tournament, weight_category=cls.weight_category,
            name="Сетка 79", system="olympic", size=2,
            data='{"rounds": [[{"a": 1, "b": 2, "bye": false}]], "participants": [1, 2], "size": 2, "byes": 0}',
        )

    def test_weighing_protocol_xlsx(self):
        from apps.core import reports

        content = reports.weighing_protocol_xlsx(self.tournament)
        self.assertGreater(len(content), 100)
        self.assertEqual(content[:2], b"PK")  # xlsx is a zip

    def test_bracket_xlsx(self):
        from apps.core import reports

        content = reports.bracket_xlsx(self.bracket)
        self.assertEqual(content[:2], b"PK")

    def test_results_docx(self):
        from apps.core import reports

        content = reports.results_docx(self.tournament)
        self.assertEqual(content[:2], b"PK")  # docx is also a zip

    def test_report_api(self):
        from rest_framework.test import APIClient

        self.tournament.set_password("rep123")
        self.tournament.save()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token rep123")

        response = client.get("/api/reports/weighing.xlsx")
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])

        response = client.get(f"/api/reports/bracket/{self.bracket.pk}.xlsx")
        self.assertEqual(response.status_code, 200)

        response = client.get("/api/reports/results.docx")
        self.assertEqual(response.status_code, 200)


class WeightParseTests(SimpleTestCase):
    def test_parse_numeric(self):
        self.assertEqual(parse_weight("до 90"), Decimal("90"))
        self.assertEqual(parse_weight("90 кг"), Decimal("90"))
        self.assertEqual(parse_weight(70.5), Decimal("70.5"))
        self.assertEqual(parse_weight("90,5"), Decimal("90.5"))
        self.assertIsNone(parse_weight(None))
        self.assertIsNone(parse_weight(""))

    def test_pick_category(self):
        category = SimpleNamespace(weight_from=50, weight_to=90, is_open=False)
        self.assertIs(pick_category([category], Decimal("70")), category)
        self.assertIsNone(pick_category([category], Decimal("91")))
        self.assertIsNone(pick_category([category], None))

    def test_pick_category_open(self):
        open_category = SimpleNamespace(weight_from=98, weight_to=None, is_open=True)
        self.assertIs(pick_category([open_category], Decimal("120")), open_category)


class PasswordTests(SimpleTestCase):
    def test_roundtrip(self):
        hashed = hash_password("secret")
        self.assertTrue(verify_password("secret", hashed))
        self.assertFalse(verify_password("wrong", hashed))

    def test_empty(self):
        self.assertEqual(hash_password(""), "")
        self.assertTrue(verify_password("anything", ""))
        self.assertFalse(verify_password("", "pbkdf2_sha256$1$a$b"))


class SlugifyTests(SimpleTestCase):
    def test_cyrillic(self):
        self.assertEqual(slugify("Кубок Москвы 2026"), "kubok-moskvy-2026")

    def test_clean(self):
        self.assertEqual(slugify("  Турнир!! По Самбо  "), "turnir-po-sambo")

    def test_empty(self):
        self.assertEqual(slugify(""), "tournament")
