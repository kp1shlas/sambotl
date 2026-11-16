"""Draw (жеребьёвка) engine.

Supports three seeding strategies and produces a bracket structure that the
preview UI renders and the bout generator turns into real :class:`Bout` rows.

Strategies
----------
``random``
    Pure shuffle — the classic "жетон из шапки" experience.
``seeded``
    Strongest athletes are placed on opposite halves of the bracket (as with
    classical seeding) so they can only meet in the final.
``mixed``
    Seeded placement for the top seeds, the rest is shuffled into the open
    slots — the most common real-world compromise.

The bracket model is a fixed-size single-elimination tree where ``size`` is the
next power of two ≥ the number of participants; spare slots become byes.
"""
import json
import random

from apps.core.enums import BoutStatus, TournamentSystem

STRATEGIES = ("random", "seeded", "mixed")


def next_power_of_two(count: int) -> int:
    size = 1
    while size < count:
        size *= 2
    return max(size, 2)


def _seed_positions(size: int) -> list[int]:
    """Classic seeding order for a bracket of ``size`` slots (1-indexed seeds)."""
    positions = [1]
    while len(positions) < size:
        mirror = len(positions) * 2 + 1
        positions = [pos for seed in positions for pos in (seed, mirror - seed)]
    return positions


def build_order(participants: list, strategy: str, rng: random.Random | None = None) -> list:
    """Return participants ordered for bracket placement (``None`` = bye)."""
    rng = rng or random.Random()
    players = list(participants)
    size = next_power_of_two(len(players))

    if strategy not in STRATEGIES:
        raise ValueError(f"Неизвестная стратегия жеребьёвки: {strategy}")

    if strategy == "random":
        rng.shuffle(players)
        slots = [*players, *([None] * (size - len(players)))]
        return slots

    # Seeded / mixed: keep the natural order as the strength ranking.
    ranking = list(players)
    if strategy == "mixed":
        head, tail = ranking[: size // 2], ranking[size // 2:]
        rng.shuffle(tail)
        ranking = head + tail
    else:
        ranking = ranking[:size]

    seeded = ranking[:2]
    rest = ranking[2:]

    slots: list = [None] * size
    placement = []

    # Seeds 1 and 2 go to opposite ends of the tree.
    if size >= 2 and seeded:
        slots[0] = seeded[0]
        placement.append(0)
    if size >= 2 and len(seeded) > 1:
        slots[size - 1] = seeded[1]
        placement.append(size - 1)

    free_positions = [index for index in range(size) if slots[index] is None]
    rng.shuffle(free_positions)

    for player, position in zip(rest, free_positions):
        slots[position] = player

    return slots


def build_bracket(participants: list, strategy: str = "mixed", system: str = TournamentSystem.OLYMPIC, rng=None) -> dict:
    """Produce a JSON-serialisable bracket structure.

    ``rounds[0]`` holds the first-round pairs, ``rounds[-1]`` holds the final.
    """
    slots = build_order(participants, strategy, rng)
    size = len(slots)

    rounds = []
    first_round = []
    for index in range(0, size, 2):
        first_round.append({
            "a": getattr(slots[index], "pk", slots[index]) if slots[index] is not None else None,
            "b": getattr(slots[index + 1], "pk", slots[index + 1]) if slots[index + 1] is not None else None,
            "bye": slots[index] is None or slots[index + 1] is None,
        })
    rounds.append(first_round)

    remaining = size // 2
    while remaining > 1:
        rounds.append([{"a": None, "b": None, "bye": False} for _ in range(remaining)])
        remaining //= 2

    return {
        "strategy": strategy,
        "system": system,
        "size": size,
        "participants": [getattr(player, "pk", player) for player in participants],
        "slots": [getattr(player, "pk", player) for player in slots],
        "rounds": rounds,
        "byes": sum(1 for pair in first_round if pair["bye"]),
    }


def save_bracket(bracket, *, strategy: str, structure: dict) -> None:
    bracket.seed_order = json.dumps(strategy)
    bracket.data = json.dumps(structure, ensure_ascii=False)
    bracket.size = structure.get("size", 0)
    bracket.is_approved = False
    bracket.save(update_fields=["seed_order", "data", "size", "is_approved", "updated_at"])


def generate_bouts(bracket) -> int:
    """Materialise the first round of ``bracket`` as :class:`Bout` rows."""
    from apps.competition.models import Bout
    from apps.participants.models import Participant

    structure = json.loads(bracket.data or "{}")
    first_round = structure.get("rounds", [[]])[0]
    participants = Participant.objects.in_bulk(structure.get("participants", []))

    # Re-draw safety: drop not-yet-started bouts of this bracket so repeated
    # draws/regenerations never duplicate pairs. Results already on the mat or
    # finished are preserved.
    Bout.objects.filter(
        bracket=bracket,
        status__in=[BoutStatus.PENDING, BoutStatus.READY],
    ).delete()

    created = 0
    for index, pair in enumerate(first_round):
        if pair.get("bye"):
            continue
        a = participants.get(pair.get("a"))
        b = participants.get(pair.get("b"))
        Bout.objects.create(
            tournament=bracket.tournament,
            bracket=bracket,
            round_no=1,
            order_in_mat=index + 1,
            participant_a=a,
            participant_b=b,
            status=BoutStatus.READY if a and b else BoutStatus.PENDING,
        )
        created += 1
    return created
