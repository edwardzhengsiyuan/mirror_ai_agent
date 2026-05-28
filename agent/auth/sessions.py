"""Signed-cookie sessions for the dashboard UI.

Why a custom session helper instead of Flask's ``flask.session``:
    * ``flask.session`` writes JSON-serialised contents into the cookie which
      grows unboundedly and is harder to audit. We only ever need ``user_id``.
    * Decoupling from ``flask.session`` keeps Flask's session interface free
      for view-layer flash messages (none today, but a common future use).
    * Using :class:`itsdangerous.URLSafeTimedSerializer` lets us specify an
      explicit max-age separately from the cookie's ``Max-Age`` attribute
      (defence in depth — even if a stolen cookie has not yet expired in
      the browser, the server will refuse to load it after the TTL).

Cookie attributes:
    HttpOnly  -- prevents JS access (XSS mitigation).
    Secure    -- HTTPS-only. Disabled when ``cookie_secure=False`` for
                 local http://localhost dev.
    SameSite=Lax -- blocks cross-site cookie leakage on top-level GETs.

Threading model:
    :class:`SessionManager` instances are immutable after construction;
    safe to share across threads. Flask stores one per app via
    ``app.extensions``.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional

from flask import Flask, Response, current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

DEFAULT_COOKIE_NAME = "mirror_session"
DEFAULT_MAX_AGE_SECONDS = 7 * 24 * 3600  # 7 days, per the agreed plan
APP_EXTENSION_KEY = "auth_session_manager"


class SessionManager:
    """Sign + verify single-string session payloads via itsdangerous.

    The payload is always the user_id. Anything else the dashboard needs
    (email, balance, etc.) is fetched from the billing store on each
    request, so a stolen cookie cannot escalate beyond impersonating a
    single user_id during the TTL.
    """

    def __init__(
        self,
        secret_key: str,
        *,
        cookie_name: str = DEFAULT_COOKIE_NAME,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
        cookie_secure: bool = True,
        cookie_samesite: str = "Lax",
        salt: str = "mirror-ai-session-v1",
    ) -> None:
        if not secret_key:
            raise ValueError("SessionManager requires a non-empty secret_key")
        self.cookie_name = cookie_name
        self.max_age_seconds = int(max_age_seconds)
        self.cookie_secure = bool(cookie_secure)
        self.cookie_samesite = cookie_samesite
        self._serializer = URLSafeTimedSerializer(secret_key, salt=salt)

    def sign(self, user_id: str) -> str:
        """Return the cookie value for ``user_id``. Opaque to the caller."""
        if not user_id:
            raise ValueError("user_id must not be empty")
        return self._serializer.dumps(user_id)

    def load(self, token: str) -> Optional[str]:
        """Return the original ``user_id`` if ``token`` is valid and unexpired.

        ``None`` is returned for any failure mode (missing, expired, tampered)
        so callers can treat them uniformly as "not logged in".
        """
        if not token:
            return None
        try:
            value = self._serializer.loads(token, max_age=self.max_age_seconds)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        if not isinstance(value, str) or not value:
            return None
        return value

    def set_cookie(self, response: Response, user_id: str) -> None:
        """Attach a freshly signed session cookie to ``response`` in-place."""
        token = self.sign(user_id)
        response.set_cookie(
            self.cookie_name,
            token,
            max_age=self.max_age_seconds,
            httponly=True,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            path="/",
        )

    def clear_cookie(self, response: Response) -> None:
        """Invalidate any existing cookie on the client. Logout entry point."""
        response.set_cookie(
            self.cookie_name,
            "",
            expires=0,
            max_age=0,
            httponly=True,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            path="/",
        )

    def install(self, app: Flask) -> None:
        """Register ``self`` on the Flask app so helpers can find it later."""
        app.extensions[APP_EXTENSION_KEY] = self


def get_session_manager() -> SessionManager:
    """Return the manager installed on ``current_app``. Raises if missing."""
    try:
        manager = current_app.extensions[APP_EXTENSION_KEY]
    except KeyError as exc:
        raise RuntimeError(
            "SessionManager not installed on Flask app. Call"
            " SessionManager(...).install(app) during create_app()."
        ) from exc
    if not isinstance(manager, SessionManager):
        raise RuntimeError(
            f"app.extensions[{APP_EXTENSION_KEY!r}] is not a SessionManager"
        )
    return manager


def current_user_id() -> Optional[str]:
    """Return the user_id from the current request's session cookie.

    Returns ``None`` if there is no cookie / it is invalid / it has expired.
    Cheap to call repeatedly: the result is memoised on ``flask.g``.
    """
    if hasattr(g, "_auth_user_id_cached"):
        return g._auth_user_id_cached  # type: ignore[attr-defined]
    manager = get_session_manager()
    token = request.cookies.get(manager.cookie_name)
    user_id = manager.load(token) if token else None
    g._auth_user_id_cached = user_id
    return user_id


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Flask view decorator: 401 if no valid session cookie.

    On success, the wrapped view can access the user_id via
    :func:`current_user_id` or directly via ``flask.g.current_user_id``.
    """

    @functools.wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        user_id = current_user_id()
        if not user_id:
            return (
                jsonify(
                    {
                        "error": {
                            "code": "unauthorized",
                            "message": "Login required.",
                        }
                    }
                ),
                401,
            )
        g.current_user_id = user_id
        return view(*args, **kwargs)

    return wrapper
