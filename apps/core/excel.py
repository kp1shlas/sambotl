"""Import of participants from an .xlsx file (Yandex Forms export or similar).

The source spreadsheet **must** contain separate columns for the name parts
(Фамилия / Имя / Отчество) — this is a hard requirement, because the judging
screens and reports print them independently.

Category resolution:
  1. if the raw "Категория" cell carries a weight limit ("до 90", "90 кг")
     we parse the number and match the weight category by its upper bound;
  2. otherwise the athlete is matched automatically by "Текущий вес"
     (falling back to "Заявленный вес" when the current one is empty).
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from openpyxl import load_workbook

from apps.core.weight import (
    looks_like_weight_category,
    parse_weight,
    pick_category,
    pick_category_by_limit,
)

FIELD_ALIASES = {
    "last_name": {"фамилия", "lastname", "last name", "surname"},
    "first_name": {"имя", "firstname", "first name", "name"},
    "middle_name": {"отчество", "middlename", "middle name", "patronymic"},
    "gender": {"пол", "gender", "sex"},
    "birth_date": {
        "дата рождения", "дата рожд", "birthdate", "birth date",
        "год рождения", "birth year", "др", "г р",
    },
    "club": {"клуб", "club", "команда", "team", "организация", "спортшкола"},
    "region": {"регион", "region", "город", "city", "область", "субъект"},
    "coach": {"тренер", "coach", "тренер фио"},
    "declared_category": {
        "категория", "весовая категория", "category", "weight category",
        "категория кг", "весовая",
    },
    "declared_weight": {
        "заявленный вес", "declared weight", "вес заявленный", "вес",
    },
    "current_weight": {
        "текущий вес", "current weight", "фактический вес", "вес факт",
    },
}

_ALIAS_LOOKUP = {
    alias: field_name
    for field_name, aliases in FIELD_ALIASES.items()
    for alias in aliases
}


def normalise_header(header) -> str:
    """Lowercase, ё→е, punctuation → single spaces."""
    text = str(header or "").strip().lower().replace("ё", "е")
    text = re.sub(r"[^0-9a-zа-я]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_gender(value) -> str:
    text = normalise_header(value)
    if text in {"м", "муж", "мужской", "m", "male", "мальчик", "юноша"}:
        return "M"
    if text in {"ж", "жен", "женский", "f", "female", "девочка", "девушка"}:
        return "F"
    return ""


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    year_only = re.fullmatch(r"(\d{4})", text)
    if year_only:
        return date(int(year_only.group(1)), 1, 1)
    return None


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recognised_columns: dict[str, str] = field(default_factory=dict)
    missing_columns: list[str] = field(default_factory=list)


def read_rows(source) -> tuple[dict[int, str], list[dict]]:
    """Return ``(column_mapping, rows)`` from the first worksheet.

    ``source`` may be a path or an uploaded file object.
    """
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        iterator = sheet.iter_rows(values_only=True)
        try:
            header_row = next(iterator)
        except StopIteration:
            return {}, []

        mapping: dict[int, str] = {}
        used: set[str] = set()
        for index, cell in enumerate(header_row):
            key = _ALIAS_LOOKUP.get(normalise_header(cell))
            if key and key not in used:
                mapping[index] = key
                used.add(key)

        rows: list[dict] = []
        for row in iterator:
            if row is None or all(
                value is None or str(value).strip() == "" for value in row
            ):
                continue
            rows.append(
                {
                    key: (row[idx] if idx < len(row) else None)
                    for idx, key in mapping.items()
                }
            )
        return mapping, rows
    finally:
        workbook.close()


REQUIRED_FIELDS = ("last_name", "first_name")

FIELD_LABELS = {
    "last_name": "Фамилия",
    "first_name": "Имя",
    "middle_name": "Отчество",
    "gender": "Пол",
    "birth_date": "Дата рождения",
    "club": "Клуб",
    "region": "Регион",
    "coach": "Тренер",
    "declared_category": "Категория",
    "declared_weight": "Заявленный вес",
    "current_weight": "Текущий вес",
}


def _resolve_age_group(groups, birth_date, gender):
    if birth_date is None:
        return None
    year = birth_date.year
    for group in groups:
        if group.gender and gender and group.gender != gender:
            continue
        if group.birth_year_from and year < group.birth_year_from:
            continue
        if group.birth_year_to and year > group.birth_year_to:
            continue
        return group
    return None


def _resolve_category(categories, raw_category, raw_current, raw_declared):
    """Return ``(category, weight, auto_detected)``."""
    weight = parse_weight(raw_current)
    if weight is None:
        weight = parse_weight(raw_declared)

    if looks_like_weight_category(raw_category):
        limit = parse_weight(raw_category)
        if limit is not None:
            match = pick_category_by_limit(categories, limit)
            if match is not None:
                return match, weight, False

    if weight is not None:
        match = pick_category(categories, weight)
        if match is not None:
            return match, weight, True

    return None, weight, False


def import_participants(tournament, source, *, dry_run: bool = False) -> ImportResult:
    """Import athletes from ``source`` into ``tournament``.

    ``dry_run=True`` runs the full validation without writing — this powers the
    admin preview step so the operator can fix the spreadsheet before import.
    """
    # Imported lazily to avoid a circular dependency at app-load time.
    from apps.competition.models import AgeGroup, WeightCategory
    from apps.participants.models import Club, Participant

    result = ImportResult()
    mapping, rows = read_rows(source)

    result.recognised_columns = {
        FIELD_LABELS.get(field_name, field_name): field_name
        for field_name in mapping.values()
    }
    result.missing_columns = [
        FIELD_LABELS[field_name]
        for field_name in REQUIRED_FIELDS
        if field_name not in mapping.values()
    ]
    if result.missing_columns:
        result.errors.append(
            "Не найдены обязательные колонки: " + ", ".join(result.missing_columns)
        )
        return result

    groups = list(AgeGroup.objects.filter(tournament=tournament))
    categories = list(WeightCategory.objects.filter(tournament=tournament))

    for line_no, row in enumerate(rows, start=2):
        last_name = str(row.get("last_name") or "").strip()
        first_name = str(row.get("first_name") or "").strip()
        middle_name = str(row.get("middle_name") or "").strip()

        if not last_name and not first_name:
            result.skipped += 1
            continue
        if not last_name or not first_name:
            result.errors.append(f"Строка {line_no}: заполнены не все части ФИО")
            result.skipped += 1
            continue

        gender = _parse_gender(row.get("gender"))
        birth_date = _parse_date(row.get("birth_date"))
        age_group = _resolve_age_group(groups, birth_date, gender)

        scoped = [
            category
            for category in categories
            if age_group is None or category.age_group_id == age_group.id
        ]
        if gender:
            same_gender = [
                category
                for category in scoped
                if not category.gender or category.gender == gender
            ]
            if same_gender:
                scoped = same_gender

        weight_category, weight, auto_detected = _resolve_category(
            scoped,
            row.get("declared_category"),
            row.get("current_weight"),
            row.get("declared_weight"),
        )
        if weight_category is None:
            result.warnings.append(
                f"Строка {line_no}: категория не определена — "
                f"«{last_name} {first_name}»"
            )

        if dry_run:
            result.created += 1
            continue

        club = None
        club_name = str(row.get("club") or "").strip()
        if club_name:
            club, _ = Club.objects.get_or_create(
                tournament=tournament, name=club_name
            )

        Participant.objects.create(
            tournament=tournament,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            gender=gender,
            birth_date=birth_date,
            age_group=age_group,
            weight_category=weight_category,
            club=club,
            region=str(row.get("region") or "").strip(),
            coach=str(row.get("coach") or "").strip(),
            declared_category=str(row.get("declared_category") or "").strip(),
            declared_weight=parse_weight(row.get("declared_weight")),
            current_weight=weight,
            category_auto_detected=auto_detected,
        )
        result.created += 1

    return result


