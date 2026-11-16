"""Bootstrap a freshly created tournament with sane defaults.

Adults get the official sport-sambo weight classes pre-filled (the customer
asked for «взрослые с заранее записанными категориями»), children get a wide
scale the operator trims down. Everything stays editable in the admin.
"""
from decimal import Decimal

from apps.core.enums import Audience, Gender, StageKind, StageStatus

# (name, lower bound, upper bound) — upper bound None means the open class.
MALE_ADULTS = [
    ("до 58 кг", None, 58), ("до 64 кг", 58, 64), ("до 71 кг", 64, 71),
    ("до 79 кг", 71, 79), ("до 88 кг", 79, 88), ("до 98 кг", 88, 98),
    ("98+ кг", 98, None),
]
FEMALE_ADULTS = [
    ("до 50 кг", None, 50), ("до 54 кг", 50, 54), ("до 59 кг", 54, 59),
    ("до 65 кг", 59, 65), ("до 72 кг", 65, 72), ("до 80 кг", 72, 80),
    ("80+ кг", 80, None),
]
MALE_CHILDREN = [
    ("до 26 кг", None, 26), ("до 29 кг", 26, 29), ("до 32 кг", 29, 32),
    ("до 35 кг", 32, 35), ("до 38 кг", 35, 38), ("до 42 кг", 38, 42),
    ("до 46 кг", 42, 46), ("до 50 кг", 46, 50), ("до 54 кг", 50, 54),
    ("до 59 кг", 54, 59), ("до 65 кг", 59, 65), ("до 71 кг", 65, 71),
    ("71+ кг", 71, None),
]
FEMALE_CHILDREN = [
    ("до 24 кг", None, 24), ("до 27 кг", 24, 27), ("до 30 кг", 27, 30),
    ("до 33 кг", 30, 33), ("до 36 кг", 33, 36), ("до 40 кг", 36, 40),
    ("до 44 кг", 40, 44), ("до 48 кг", 44, 48), ("до 52 кг", 48, 52),
    ("до 57 кг", 52, 57), ("до 62 кг", 57, 62), ("62+ кг", 62, None),
]

_GENDER_LABEL = {Gender.MALE: "муж.", Gender.FEMALE: "жен."}

STAGE_SEQUENCE = [
    StageKind.SETUP,
    StageKind.REGISTRATION,
    StageKind.WEIGHING,
    StageKind.DRAW,
    StageKind.MAT_ASSIGNMENT,
    StageKind.COMPETITION,
    StageKind.FINISHED,
]


def _seed_categories(tournament, audience: str) -> None:
    from apps.competition.models import AgeGroup, WeightCategory

    plans = []
    if audience in (Audience.ADULTS, Audience.MIXED):
        plans.append(("Взрослые", Gender.MALE, MALE_ADULTS, False))
        plans.append(("Взрослые", Gender.FEMALE, FEMALE_ADULTS, False))
    if audience in (Audience.CHILDREN, Audience.MIXED):
        plans.append(("Юноши", Gender.MALE, MALE_CHILDREN, True))
        plans.append(("Девушки", Gender.FEMALE, FEMALE_CHILDREN, True))

    for order, (label, gender, classes, is_children) in enumerate(plans):
        group = AgeGroup.objects.create(
            tournament=tournament,
            name=f"{label} ({_GENDER_LABEL[gender]})",
            gender=gender,
            is_children=is_children,
            order=order,
        )
        for index, (name, weight_from, weight_to) in enumerate(classes):
            WeightCategory.objects.create(
                tournament=tournament,
                age_group=group,
                name=name,
                gender=gender,
                weight_from=Decimal(weight_from) if weight_from is not None else None,
                weight_to=Decimal(weight_to) if weight_to is not None else None,
                is_open=weight_to is None,
                order=index,
            )


def _seed_stages(tournament) -> None:
    from apps.tournaments.models import Stage

    for order, kind in enumerate(STAGE_SEQUENCE):
        Stage.objects.create(
            tournament=tournament,
            kind=kind,
            status=StageStatus.IN_PROGRESS if order == 0 else StageStatus.PENDING,
        )


def bootstrap_tournament(
    *,
    name: str,
    system: str,
    audience: str,
    mats: int = 4,
    association: str = "",
    password_hash: str = "",
):
    """Create the single Tournament record with mats, categories and stages."""
    from apps.competition.models import Mat
    from apps.tournaments.models import Tournament

    tournament = Tournament.objects.create(
        name=name,
        association=association,
        system=system,
        audience=audience,
        mats_count=mats,
        access_password=password_hash,
    )

    for number in range(1, max(mats, 1) + 1):
        Mat.objects.create(tournament=tournament, number=number)

    _seed_categories(tournament, audience)
    _seed_stages(tournament)
    return tournament
