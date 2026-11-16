"""Weight parsing / category matching helpers.

Handles the two ways a category reaches the system:
  * the raw "category" column from Excel may contain a weight limit
    ("до 90", "90 кг", "до 90 кг") — we parse the number and match it;
  * when the category is missing the athlete is matched by *current weight*.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


def parse_weight(value) -> Optional[Decimal]:
    """Extract the first numeric (kg) value from a raw cell value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    match = _NUM_RE.search(str(value).replace(",", "."))
    if not match:
        return None
    try:
        return Decimal(match.group(1))
    except InvalidOperation:  # pragma: no cover - defensive
        return None


def looks_like_weight_category(value) -> bool:
    """True when the raw category cell carries a numeric weight limit."""
    if value is None:
        return False
    return bool(_NUM_RE.search(str(value)))


def pick_category(categories: Iterable, weight: Optional[Decimal]):
    """Return the tightest category that contains ``weight``.

    Categories are compared by duck typing: ``weight_from`` (lower bound, may be
    ``None``) and ``weight_to`` (upper bound; ``None`` = heaviest, open class).
    """
    if weight is None:
        return None
    best = None
    best_lower = None
    for category in categories:
        lower = getattr(category, "weight_from", None)
        upper = getattr(category, "weight_to", None)
        if lower is not None and weight < Decimal(lower):
            continue
        if upper is not None and weight > Decimal(upper):
            continue
        if best_lower is None or (lower is not None and Decimal(lower) > best_lower):
            best, best_lower = category, (Decimal(lower) if lower is not None else None)
    return best


def pick_category_by_limit(categories: Iterable, limit: Decimal):
    """Return the category whose upper bound equals ``limit`` (parsed 'до N')."""
    exact = None
    fallback = None
    for category in categories:
        upper = getattr(category, "weight_to", None)
        if upper is None:
            if fallback is None and getattr(category, "is_open", False):
                fallback = category
            continue
        if Decimal(upper) == limit:
            return category
        if Decimal(upper) >= limit:
            fallback = category
    return exact or fallback
