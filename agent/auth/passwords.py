"""Password hashing wrappers.

Why a thin module instead of inlining ``werkzeug.security`` calls:
    1. Single point of change if we ever migrate to bcrypt / argon2.
    2. The function signatures here document intent (``hash_password`` /
       ``verify_password``) rather than leaking algorithm names into
       business code.

Algorithm:
    PBKDF2-HMAC-SHA256 via :func:`werkzeug.security.generate_password_hash`.
    The hash format produced (``pbkdf2:sha256:<iterations>$<salt>$<hash>``)
    is self-describing, so future readers do not need to remember the
    iteration count. Werkzeug picks a sensible default for current hardware.
"""

from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    """Return an opaque hash string suitable for persisting on the user row.

    Raises:
        ValueError: if ``password`` is empty (defensive — endpoints already
            validate length, but the helper rejects ``""`` as a final fence).
    """
    if not password:
        raise ValueError("password must not be empty")
    return generate_password_hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Constant-time check of a candidate ``password`` against ``stored_hash``.

    Treats missing inputs as a non-match rather than raising — keeps the
    caller's flow simple (``if not verify_password(...): return 401`` works
    whether the user lacks a password_hash entirely or the password is wrong).
    """
    if not password or not stored_hash:
        return False
    try:
        return check_password_hash(stored_hash, password)
    except ValueError:
        # generate_password_hash output that is somehow malformed (e.g. a
        # legacy row written by hand). Treat as non-match rather than crash.
        return False
