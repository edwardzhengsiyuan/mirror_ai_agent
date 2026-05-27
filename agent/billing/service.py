"""High-level billing operations.

This module composes :class:`BillingStore` primitives into the operations the
HTTP layer actually wants:

    * authenticate an API key
    * charge before serving a request
    * settle / refund after the request finishes
    * topup credits
    * issue / revoke API keys
    * fetch balance and usage history

All write operations are idempotent on ``request_id``: replaying the same
``request_id`` returns the existing receipt instead of double-charging or
double-refunding. This lets callers retry without fear.
"""

from __future__ import annotations

import datetime as dt
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from .errors import (
    DuplicateRequestError,
    InflightLimitError,
    InsufficientFundsError,
    RateLimitError,
    UnknownApiKeyError,
    UnknownUserError,
)
from .store import BillingStore, _now_iso, hash_api_key


@dataclass
class ChargeReceipt:
    request_id: str
    user_id: str
    endpoint: str
    amount_credits: int
    balance_after: int
    status: str  # 'pending' | 'settled' | 'refunded'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BillingService:
    def __init__(
        self,
        store: BillingStore,
        inflight_limit: int = 2,
        rate_limit_per_minute: int = 10,
    ) -> None:
        self.store = store
        self.inflight_limit = max(1, int(inflight_limit))
        self.rate_limit_per_minute = max(1, int(rate_limit_per_minute))

    # ------------------------------------------------------------------
    # auth
    # ------------------------------------------------------------------

    def authenticate(self, plaintext_key: str) -> Dict[str, Any]:
        """Resolve a plaintext API key to ``{user_id, key_hash, balance, ...}``.

        Raises :class:`UnknownApiKeyError` if the key is missing, revoked, or
        the user is disabled.
        """
        key = (plaintext_key or "").strip()
        if not key:
            raise UnknownApiKeyError("missing api key")
        record = self.store.lookup_api_key(key)
        if record is None:
            raise UnknownApiKeyError("unknown api key")
        if record.get("revoked"):
            raise UnknownApiKeyError("api key revoked")
        if record.get("user_status") != "active":
            raise UnknownApiKeyError("user disabled")
        # Touch best-effort; failures here must not break auth.
        try:
            self.store.touch_api_key(record["api_key_hash"])
        except Exception:
            pass
        return {
            "user_id": record["user_id"],
            "key_hash": record["api_key_hash"],
            "label": record.get("label"),
            "balance_credits": record["balance_credits"],
            "daily_credits_limit": record.get("daily_credits_limit"),
        }

    # ------------------------------------------------------------------
    # rate limit (per api key, sliding 60s window)
    # ------------------------------------------------------------------

    def check_rate_limit(self, scope: str) -> None:
        if self.rate_limit_per_minute <= 0:
            return
        now_epoch = int(time.time())
        window_start = now_epoch - 60
        recent = self.store.count_rate_events(scope, window_start)
        if recent >= self.rate_limit_per_minute:
            raise RateLimitError(scope, self.rate_limit_per_minute, 60)
        self.store.record_rate_event(scope, now_epoch)
        # Best-effort prune of old events to keep the table small.
        if recent == 0:
            self.store.prune_rate_events(now_epoch - 600)

    # ------------------------------------------------------------------
    # charge / settle / refund
    # ------------------------------------------------------------------

    def charge(
        self,
        user_id: str,
        endpoint: str,
        amount_credits: int,
        request_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> ChargeReceipt:
        """Atomically reserve credits for a request.

        Raises:
            UnknownUserError: user not found
            InflightLimitError: too many concurrent requests for this user
            InsufficientFundsError: balance below ``amount_credits`` or status disabled
            DuplicateRequestError: ``request_id`` already used (carries existing balance)
        """
        if amount_credits < 0:
            raise ValueError("amount_credits must be >= 0")
        request_id = request_id or str(uuid.uuid4())
        now = _now_iso()
        meta_json = self.store.to_meta_json(meta)

        with self.store.transaction() as conn:
            user_row = conn.execute(
                "SELECT balance_credits, status FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if user_row is None:
                raise UnknownUserError(user_id)
            if user_row["status"] != "active":
                raise InsufficientFundsError(f"user {user_id} is {user_row['status']}")

            existing = conn.execute(
                "SELECT balance_after, kind, status FROM ledger WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if existing is not None:
                raise DuplicateRequestError(request_id, int(existing["balance_after"]))

            inflight_n = conn.execute(
                "SELECT COUNT(*) AS n FROM inflight WHERE user_id = ?",
                (user_id,),
            ).fetchone()["n"]
            if inflight_n >= self.inflight_limit:
                raise InflightLimitError(user_id, self.inflight_limit, int(inflight_n))

            if amount_credits > 0:
                cur = conn.execute(
                    "UPDATE users SET balance_credits = balance_credits - ?,"
                    " updated_at = ? WHERE user_id = ? AND balance_credits >= ?"
                    " AND status = 'active'",
                    (int(amount_credits), now, user_id, int(amount_credits)),
                )
                if cur.rowcount == 0:
                    raise InsufficientFundsError(
                        f"user {user_id} balance < {amount_credits}"
                    )

            balance_after = conn.execute(
                "SELECT balance_credits FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()["balance_credits"]

            conn.execute(
                "INSERT INTO ledger (user_id, request_id, endpoint, kind,"
                " amount_credits, balance_after, status, meta_json, ts)"
                " VALUES (?, ?, ?, 'charge', ?, ?, 'pending', ?, ?)",
                (
                    user_id,
                    request_id,
                    endpoint,
                    int(amount_credits),
                    int(balance_after),
                    meta_json,
                    now,
                ),
            )
            conn.execute(
                "INSERT INTO inflight (request_id, user_id, endpoint, started_at)"
                " VALUES (?, ?, ?, ?)",
                (request_id, user_id, endpoint, now),
            )

        return ChargeReceipt(
            request_id=request_id,
            user_id=user_id,
            endpoint=endpoint,
            amount_credits=int(amount_credits),
            balance_after=int(balance_after),
            status="pending",
        )

    def settle(self, request_id: str) -> Optional[ChargeReceipt]:
        """Mark a pending charge as settled. Idempotent."""
        with self.store.transaction() as conn:
            row = conn.execute(
                "SELECT user_id, endpoint, amount_credits, balance_after, status"
                " FROM ledger WHERE request_id = ? AND kind = 'charge'",
                (request_id,),
            ).fetchone()
            if row is None:
                return None
            if row["status"] == "pending":
                conn.execute(
                    "UPDATE ledger SET status = 'settled' WHERE request_id = ?"
                    " AND kind = 'charge'",
                    (request_id,),
                )
            conn.execute("DELETE FROM inflight WHERE request_id = ?", (request_id,))
        return ChargeReceipt(
            request_id=request_id,
            user_id=row["user_id"],
            endpoint=row["endpoint"] or "",
            amount_credits=int(row["amount_credits"]),
            balance_after=int(row["balance_after"]),
            status="settled",
        )

    def refund(
        self,
        request_id: str,
        reason: Optional[str] = None,
    ) -> Optional[ChargeReceipt]:
        """Reverse a charge.

        Adds the credits back, writes a sibling ``refund`` ledger row, marks
        the original charge ``refunded``, and clears any inflight slot.
        Idempotent: a second call after refund returns the same receipt.
        """
        refund_request_id = f"{request_id}::refund"
        with self.store.transaction() as conn:
            row = conn.execute(
                "SELECT user_id, endpoint, amount_credits, status FROM ledger"
                " WHERE request_id = ? AND kind = 'charge'",
                (request_id,),
            ).fetchone()
            if row is None:
                return None

            already_refunded = conn.execute(
                "SELECT balance_after FROM ledger WHERE request_id = ?",
                (refund_request_id,),
            ).fetchone()
            if already_refunded is not None:
                conn.execute("DELETE FROM inflight WHERE request_id = ?", (request_id,))
                return ChargeReceipt(
                    request_id=request_id,
                    user_id=row["user_id"],
                    endpoint=row["endpoint"] or "",
                    amount_credits=int(row["amount_credits"]),
                    balance_after=int(already_refunded["balance_after"]),
                    status="refunded",
                )

            amount = int(row["amount_credits"])
            now = _now_iso()
            if amount > 0:
                conn.execute(
                    "UPDATE users SET balance_credits = balance_credits + ?,"
                    " updated_at = ? WHERE user_id = ?",
                    (amount, now, row["user_id"]),
                )
            balance_after = conn.execute(
                "SELECT balance_credits FROM users WHERE user_id = ?",
                (row["user_id"],),
            ).fetchone()["balance_credits"]

            meta_json = self.store.to_meta_json({"reason": reason} if reason else None)
            conn.execute(
                "INSERT INTO ledger (user_id, request_id, endpoint, kind,"
                " amount_credits, balance_after, status, meta_json, ts)"
                " VALUES (?, ?, ?, 'refund', ?, ?, 'settled', ?, ?)",
                (
                    row["user_id"],
                    refund_request_id,
                    row["endpoint"],
                    amount,
                    int(balance_after),
                    meta_json,
                    now,
                ),
            )
            conn.execute(
                "UPDATE ledger SET status = 'refunded' WHERE request_id = ?"
                " AND kind = 'charge'",
                (request_id,),
            )
            conn.execute("DELETE FROM inflight WHERE request_id = ?", (request_id,))

        return ChargeReceipt(
            request_id=request_id,
            user_id=row["user_id"],
            endpoint=row["endpoint"] or "",
            amount_credits=amount,
            balance_after=int(balance_after),
            status="refunded",
        )

    # ------------------------------------------------------------------
    # topup
    # ------------------------------------------------------------------

    def topup(
        self,
        user_id: str,
        amount_credits: int,
        request_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> ChargeReceipt:
        if amount_credits <= 0:
            raise ValueError("topup amount must be positive")
        request_id = request_id or f"topup-{uuid.uuid4()}"
        now = _now_iso()
        meta_json = self.store.to_meta_json(meta)
        with self.store.transaction() as conn:
            user_row = conn.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if user_row is None:
                raise UnknownUserError(user_id)

            existing = conn.execute(
                "SELECT balance_after, kind FROM ledger WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if existing is not None:
                raise DuplicateRequestError(request_id, int(existing["balance_after"]))

            conn.execute(
                "UPDATE users SET balance_credits = balance_credits + ?,"
                " updated_at = ? WHERE user_id = ?",
                (int(amount_credits), now, user_id),
            )
            balance_after = conn.execute(
                "SELECT balance_credits FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()["balance_credits"]
            conn.execute(
                "INSERT INTO ledger (user_id, request_id, endpoint, kind,"
                " amount_credits, balance_after, status, meta_json, ts)"
                " VALUES (?, ?, NULL, 'topup', ?, ?, 'settled', ?, ?)",
                (
                    user_id,
                    request_id,
                    int(amount_credits),
                    int(balance_after),
                    meta_json,
                    now,
                ),
            )
        return ChargeReceipt(
            request_id=request_id,
            user_id=user_id,
            endpoint="",
            amount_credits=int(amount_credits),
            balance_after=int(balance_after),
            status="settled",
        )

    # ------------------------------------------------------------------
    # users / api keys
    # ------------------------------------------------------------------

    def create_user(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        initial_credits: int = 0,
        daily_credits_limit: Optional[int] = None,
        issue_first_key: bool = True,
        key_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a user, optionally with an initial topup and first API key."""
        existing = self.store.get_user(user_id)
        if existing is not None:
            raise ValueError(f"user {user_id} already exists")
        user = self.store.create_user(
            user_id=user_id,
            display_name=display_name,
            initial_credits=0,
            daily_credits_limit=daily_credits_limit,
        )
        plaintext_key: Optional[str] = None
        if issue_first_key:
            plaintext_key, _ = self.store.issue_api_key(user_id, key_label or "primary")
        if initial_credits > 0:
            receipt = self.topup(
                user_id,
                initial_credits,
                meta={"source": "create_user"},
            )
            user["balance_credits"] = receipt.balance_after
        return {
            "user": user,
            "api_key_plaintext": plaintext_key,
        }

    def issue_api_key(self, user_id: str, label: Optional[str] = None) -> str:
        if self.store.get_user(user_id) is None:
            raise UnknownUserError(user_id)
        plaintext, _ = self.store.issue_api_key(user_id, label)
        return plaintext

    def revoke_api_key(self, plaintext_or_hash: str) -> bool:
        """Revoke by plaintext or by ``api_key_hash``."""
        candidate = (plaintext_or_hash or "").strip()
        if not candidate:
            return False
        # If it doesn't look like a hex digest, treat as plaintext.
        is_hex_digest = len(candidate) == 64 and all(
            c in "0123456789abcdef" for c in candidate.lower()
        )
        key_hash = candidate.lower() if is_hex_digest else hash_api_key(candidate)
        return self.store.revoke_api_key(key_hash)

    def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        return self.store.list_api_keys(user_id)

    def get_balance(self, user_id: str) -> int:
        user = self.store.get_user(user_id)
        if user is None:
            raise UnknownUserError(user_id)
        return int(user["balance_credits"])

    def list_usage(
        self,
        user_id: str,
        limit: int = 50,
        since_iso: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.store.list_ledger(user_id=user_id, limit=limit, since_iso=since_iso)

    # ------------------------------------------------------------------
    # admin helpers
    # ------------------------------------------------------------------

    def admin_list_users(self, limit: int = 200) -> List[Dict[str, Any]]:
        return self.store.list_users(limit=limit)

    def admin_list_ledger(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return self.store.list_ledger(user_id=user_id, limit=limit)

    def admin_set_user_status(self, user_id: str, status: str) -> None:
        if self.store.get_user(user_id) is None:
            raise UnknownUserError(user_id)
        self.store.set_user_status(user_id, status)


def utc_iso_offset_from_now(seconds: int) -> str:
    """Helper: ISO-8601 UTC timestamp ``seconds`` ago. Useful for usage queries."""
    return (dt.datetime.now(dt.UTC) - dt.timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )
