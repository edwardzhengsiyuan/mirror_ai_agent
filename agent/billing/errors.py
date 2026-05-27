"""Exceptions raised by the billing module."""

from __future__ import annotations


class BillingError(Exception):
    """Base class for billing failures."""


class InsufficientFundsError(BillingError):
    """The user does not have enough credits or is disabled."""


class UnknownUserError(BillingError):
    """No user matches the supplied user_id."""


class UnknownApiKeyError(BillingError):
    """The supplied API key is missing, revoked, or unknown."""


class DuplicateRequestError(BillingError):
    """A ledger entry already exists for this ``request_id``."""

    def __init__(self, request_id: str, balance_after: int) -> None:
        super().__init__(f"duplicate request_id={request_id}")
        self.request_id = request_id
        self.balance_after = balance_after


class InflightLimitError(BillingError):
    """The user already has too many in-flight requests."""

    def __init__(self, user_id: str, limit: int, current: int) -> None:
        super().__init__(f"inflight limit reached for user={user_id} ({current}/{limit})")
        self.user_id = user_id
        self.limit = limit
        self.current = current


class RateLimitError(BillingError):
    """The API key has exceeded its short-window request rate."""

    def __init__(self, scope: str, limit: int, window_seconds: int) -> None:
        super().__init__(
            f"rate limit exceeded scope={scope} limit={limit}/{window_seconds}s"
        )
        self.scope = scope
        self.limit = limit
        self.window_seconds = window_seconds
