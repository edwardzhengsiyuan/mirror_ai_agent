"""SQLite-backed billing store.

A single :class:`BillingStore` owns the underlying ``billing.db`` file and
exposes low-level CRUD operations. Higher-level orchestration (charge /
refund / rate-limit) lives in :mod:`agent.billing.service`.

Concurrency model:
    * SQLite is opened in WAL mode so multiple readers can run in parallel
      with a single writer.
    * Each method opens a fresh connection (fast on Windows; cheap on Linux),
      enabling thread-safety without sharing connections across threads.
    * Write transactions use ``BEGIN IMMEDIATE`` to take the writer lock up
      front and avoid mid-statement ``SQLITE_BUSY`` upgrades.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id              TEXT PRIMARY KEY,
    display_name         TEXT,
    balance_credits      INTEGER NOT NULL DEFAULT 0,
    status               TEXT NOT NULL DEFAULT 'active',
    daily_credits_limit  INTEGER,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    email                TEXT,
    password_hash        TEXT,
    verified_at          TEXT
);

CREATE TABLE IF NOT EXISTS api_keys (
    api_key_hash   TEXT PRIMARY KEY,
    user_id        TEXT NOT NULL,
    label          TEXT,
    created_at     TEXT NOT NULL,
    last_seen_at   TEXT,
    revoked        INTEGER NOT NULL DEFAULT 0,
    plaintext      TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

CREATE TABLE IF NOT EXISTS ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    request_id      TEXT NOT NULL UNIQUE,
    endpoint        TEXT,
    kind            TEXT NOT NULL,
    amount_credits  INTEGER NOT NULL,
    balance_after   INTEGER NOT NULL,
    status          TEXT NOT NULL,
    meta_json       TEXT,
    ts              TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ledger_user_ts ON ledger(user_id, ts);
CREATE INDEX IF NOT EXISTS idx_ledger_endpoint ON ledger(endpoint);

CREATE TABLE IF NOT EXISTS inflight (
    request_id  TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    endpoint    TEXT NOT NULL,
    started_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_inflight_user ON inflight(user_id);

CREATE TABLE IF NOT EXISTS rate_events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    scope     TEXT NOT NULL,
    ts_epoch  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rate_events_scope_ts ON rate_events(scope, ts_epoch);
"""


# Indexes that reference columns added by ``_migrate_post_release_columns``.
# These must run AFTER migration on an old database (otherwise the indexed
# column does not exist yet). Safe to re-run; CREATE INDEX IF NOT EXISTS is
# a no-op once the index is present.
POST_MIGRATION_SQL = """
-- Partial unique index so legacy users (email IS NULL) do not collide.
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
    ON users(email) WHERE email IS NOT NULL;
"""


def _now_iso() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def hash_api_key(plaintext: str) -> str:
    """SHA-256 hex digest used as the lookup key for an API key."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    """Generate a fresh URL-safe API key (43 chars, ~256 bits entropy)."""
    return secrets.token_urlsafe(32)


class EmailAlreadyRegisteredError(ValueError):
    """Raised when create_user is called with an email that already exists.

    The service / endpoint layer maps this to a 409 ``email_taken`` error.
    """

    def __init__(self, email: str) -> None:
        super().__init__(f"email already registered: {email}")
        self.email = email


# Columns added after the initial SCHEMA_SQL release. For each table we list
# (column_name, DDL fragment used in ALTER TABLE). The migration step at startup
# inspects the live database with PRAGMA table_info and adds any missing column.
# All new columns must be nullable (or have a default) because SQLite cannot add
# a NOT NULL column without a default to a table that already has rows.
_POST_RELEASE_COLUMNS: Dict[str, List[Tuple[str, str]]] = {
    "users": [
        ("email", "TEXT"),
        ("password_hash", "TEXT"),
        ("verified_at", "TEXT"),
    ],
    "api_keys": [
        ("plaintext", "TEXT"),
    ],
}


class BillingStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with self._connect() as conn:
            # Order matters: SCHEMA_SQL handles fresh databases and any old
            # tables that still need standalone CREATE TABLE statements;
            # _migrate_post_release_columns ALTERs old tables to add the new
            # columns; only then is POST_MIGRATION_SQL safe to run because
            # its indexes reference the migrated columns.
            conn.executescript(SCHEMA_SQL)
            self._migrate_post_release_columns(conn)
            conn.executescript(POST_MIGRATION_SQL)
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")

    def _migrate_post_release_columns(self, conn: sqlite3.Connection) -> None:
        """Add columns that were introduced after the initial SCHEMA_SQL.

        SQLite has no ``ALTER TABLE IF COLUMN EXISTS`` so we look at
        ``PRAGMA table_info`` and issue ``ALTER TABLE ADD COLUMN`` per missing
        column. Safe to run repeatedly; no-op once everything is present.
        """
        for table, columns in _POST_RELEASE_COLUMNS.items():
            existing = {
                row["name"] for row in conn.execute(f"PRAGMA table_info({table})")
            }
            if not existing:
                # Table itself does not exist yet — SCHEMA_SQL above would have
                # created it on a fresh database, so this branch only fires if
                # someone removed the CREATE TABLE statement. Skip.
                continue
            for col_name, col_ddl in columns:
                if col_name in existing:
                    continue
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_ddl}")

    # ------------------------------------------------------------------
    # connection helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------

    _USER_COLUMNS = (
        "user_id, display_name, balance_credits, status,"
        " daily_credits_limit, created_at, updated_at,"
        " email, password_hash, verified_at"
    )

    def create_user(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        initial_credits: int = 0,
        daily_credits_limit: Optional[int] = None,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = _now_iso()
        try:
            with self.transaction() as conn:
                conn.execute(
                    "INSERT INTO users (user_id, display_name, balance_credits, status,"
                    " daily_credits_limit, created_at, updated_at, email, password_hash)"
                    " VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        display_name,
                        int(initial_credits),
                        daily_credits_limit,
                        now,
                        now,
                        email,
                        password_hash,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            # Surface a clearer error so callers can distinguish duplicate
            # user_id from duplicate email. Service layer relies on
            # exception message to map to API error codes.
            msg = str(exc).lower()
            if "users.email" in msg or "idx_users_email" in msg:
                raise EmailAlreadyRegisteredError(email or "") from exc
            raise
        user = self.get_user(user_id)
        if user is None:
            # Should never happen: row was just inserted in same transaction.
            raise RuntimeError(f"created user {user_id} but cannot read it back")
        return user

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {self._USER_COLUMNS} FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        if not email:
            return None
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {self._USER_COLUMNS} FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        return dict(row) if row else None

    def list_users(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {self._USER_COLUMNS}"
                " FROM users ORDER BY created_at DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return [dict(r) for r in rows]

    def set_user_status(self, user_id: str, status: str) -> None:
        if status not in ("active", "disabled"):
            raise ValueError(f"invalid status: {status}")
        with self.transaction() as conn:
            conn.execute(
                "UPDATE users SET status = ?, updated_at = ? WHERE user_id = ?",
                (status, _now_iso(), user_id),
            )

    def update_user_password(self, user_id: str, password_hash: str) -> bool:
        with self.transaction() as conn:
            cur = conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
                (password_hash, _now_iso(), user_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # api keys
    # ------------------------------------------------------------------

    def issue_api_key(
        self,
        user_id: str,
        label: Optional[str] = None,
        store_plaintext: bool = False,
    ) -> Tuple[str, str]:
        """Issue a fresh key. Returns ``(plaintext, key_hash)``.

        Args:
            user_id: owner.
            label: human-readable name (e.g. ``"primary"``).
            store_plaintext: when True, persist the plaintext on the row so
                the dashboard can re-display it later. When False (legacy
                /v1/register flow, /v1/api_keys [POST]), the plaintext is
                only returned to the caller once and never stored.
        """
        plaintext = generate_api_key()
        key_hash = hash_api_key(plaintext)
        now = _now_iso()
        stored = plaintext if store_plaintext else None
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO api_keys (api_key_hash, user_id, label, created_at,"
                " last_seen_at, revoked, plaintext)"
                " VALUES (?, ?, ?, ?, NULL, 0, ?)",
                (key_hash, user_id, label, now, stored),
            )
        return plaintext, key_hash

    def lookup_api_key(self, plaintext: str) -> Optional[Dict[str, Any]]:
        if not plaintext:
            return None
        key_hash = hash_api_key(plaintext)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT k.api_key_hash, k.user_id, k.label, k.created_at,"
                " k.last_seen_at, k.revoked, u.status AS user_status,"
                " u.balance_credits, u.daily_credits_limit"
                " FROM api_keys k JOIN users u ON u.user_id = k.user_id"
                " WHERE k.api_key_hash = ?",
                (key_hash,),
            ).fetchone()
        return dict(row) if row else None

    def touch_api_key(self, key_hash: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE api_keys SET last_seen_at = ? WHERE api_key_hash = ?",
                (_now_iso(), key_hash),
            )

    def revoke_api_key(self, key_hash: str) -> bool:
        with self.transaction() as conn:
            cur = conn.execute(
                "UPDATE api_keys SET revoked = 1, plaintext = NULL"
                " WHERE api_key_hash = ? AND revoked = 0",
                (key_hash,),
            )
            return cur.rowcount > 0

    def revoke_all_user_api_keys(self, user_id: str) -> int:
        """Revoke every non-revoked key for ``user_id``. Returns count revoked.

        Used by /v1/me/api_key/rotate so the dashboard's single-key UX has a
        clean slate before issuing the replacement.
        """
        with self.transaction() as conn:
            cur = conn.execute(
                "UPDATE api_keys SET revoked = 1, plaintext = NULL"
                " WHERE user_id = ? AND revoked = 0",
                (user_id,),
            )
            return cur.rowcount

    def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT api_key_hash, label, created_at, last_seen_at, revoked, plaintext"
                " FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_current_user_api_key(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Return the most recent non-revoked key row for ``user_id``.

        Includes ``plaintext`` when persisted (auth-flow keys). The dashboard
        shows it directly; legacy keys (curl-only registration) show as masked.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT api_key_hash, label, created_at, last_seen_at, revoked, plaintext"
                " FROM api_keys WHERE user_id = ? AND revoked = 0"
                " ORDER BY created_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # ledger writes (low level — service.py builds higher-level flows)
    # ------------------------------------------------------------------

    def update_ledger_meta(self, request_id: str, patch: Dict[str, Any]) -> bool:
        """Merge ``patch`` into the ledger row's ``meta_json``.

        Only updates rows where ``kind = 'charge'`` (the post-call billing
        layer attaches LLM usage / latency stats to the charge entry, not to
        refund or topup rows). Returns True if a row was updated.
        """
        if not patch:
            return False
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT meta_json FROM ledger WHERE request_id = ? AND kind = 'charge'",
                (request_id,),
            ).fetchone()
            if row is None:
                return False
            current: Dict[str, Any] = {}
            if row["meta_json"]:
                try:
                    parsed = json.loads(row["meta_json"])
                    if isinstance(parsed, dict):
                        current = parsed
                except (TypeError, ValueError):
                    current = {}
            current.update(patch)
            try:
                merged = json.dumps(current, ensure_ascii=False, sort_keys=True)
            except (TypeError, ValueError):
                merged = json.dumps({"_serialize_error": True})
            conn.execute(
                "UPDATE ledger SET meta_json = ? WHERE request_id = ? AND kind = 'charge'",
                (merged, request_id),
            )
        return True

    def find_ledger(self, request_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, user_id, request_id, endpoint, kind, amount_credits,"
                " balance_after, status, meta_json, ts FROM ledger WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_ledger(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        since_iso: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if since_iso:
            clauses.append("ts >= ?")
            params.append(since_iso)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(max(1, int(limit)))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, user_id, request_id, endpoint, kind, amount_credits,"
                " balance_after, status, meta_json, ts FROM ledger"
                + where
                + " ORDER BY id DESC LIMIT ?",
                params,
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # inflight
    # ------------------------------------------------------------------

    def count_inflight(self, user_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM inflight WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return int(row["n"]) if row else 0

    def remove_inflight(self, request_id: str) -> None:
        with self.transaction() as conn:
            conn.execute("DELETE FROM inflight WHERE request_id = ?", (request_id,))

    # ------------------------------------------------------------------
    # rate limit (simple sliding-window counter table)
    # ------------------------------------------------------------------

    def record_rate_event(self, scope: str, ts_epoch: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO rate_events (scope, ts_epoch) VALUES (?, ?)",
                (scope, int(ts_epoch)),
            )

    def count_rate_events(self, scope: str, since_epoch: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM rate_events WHERE scope = ? AND ts_epoch >= ?",
                (scope, int(since_epoch)),
            ).fetchone()
        return int(row["n"]) if row else 0

    def prune_rate_events(self, before_epoch: int) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                "DELETE FROM rate_events WHERE ts_epoch < ?",
                (int(before_epoch),),
            )
            return cur.rowcount

    # ------------------------------------------------------------------
    # debug / maintenance
    # ------------------------------------------------------------------

    def to_meta_json(self, meta: Optional[Dict[str, Any]]) -> Optional[str]:
        if not meta:
            return None
        try:
            return json.dumps(meta, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            return json.dumps({"_serialize_error": True})
