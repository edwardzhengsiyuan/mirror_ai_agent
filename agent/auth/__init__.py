"""User authentication: password hashing + signed-cookie sessions.

This package is intentionally kept independent from :mod:`agent.billing` so
the password / session logic stays portable (could be reused for an admin
UI, OAuth flow, etc.). It does, however, depend on the same SQLite store
because user identity columns (``email``, ``password_hash``) live on the
``users`` table managed by :class:`agent.billing.store.BillingStore`.

Public API:
    :func:`hash_password`, :func:`verify_password` -- password hashing
        (currently PBKDF2 via werkzeug; swappable later).
    :class:`SessionManager`  -- signed-cookie session helper (set / read /
        clear) backed by :mod:`itsdangerous`.
    :func:`login_required` / :func:`current_user_id` -- Flask request-scope
        helpers built around ``SessionManager``.
"""

from .passwords import hash_password, verify_password
from .sessions import (
    SessionManager,
    current_user_id,
    login_required,
)

__all__ = [
    "hash_password",
    "verify_password",
    "SessionManager",
    "current_user_id",
    "login_required",
]
