"""Password hashing for LAN client access.

The operator sets one shared access password per tournament (see the customer
brief). Stage operators only need that code to open their client screen, while
the full Django admin keeps its own separate login.
"""
import hashlib
import hmac
import secrets

_ITERATIONS = 200_000


def hash_password(raw: str) -> str:
    """Return ``pbkdf2_sha256$iterations$salt$hash`` or ``""`` for empty input."""
    if not raw:
        return ""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", raw.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${digest}"


def verify_password(raw: str, stored: str) -> bool:
    if not stored:
        return True  # password not configured => open access
    if not raw:
        return False
    try:
        algorithm, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", raw.encode("utf-8"), salt.encode("utf-8"), int(iterations)
    ).hex()
    return hmac.compare_digest(candidate, digest)
