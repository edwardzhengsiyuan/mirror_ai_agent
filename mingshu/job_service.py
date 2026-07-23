"""Persistent background jobs for generating printable MingShu reports."""

from __future__ import annotations

import json
import os
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable


JobRunner = Callable[[str, dict[str, Any], Path, Callable[[int, str], None]], dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class MingshuJobService:
    """Small persistent queue suitable for one MirrorAI application instance."""

    def __init__(self, root: str | Path, runner: JobRunner, *, max_workers: int = 1) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.runner = runner
        self.executor = ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="mingshu",
        )
        self._lock = threading.RLock()
        try:
            self.retention_hours = max(
                1,
                int(os.environ.get("MINGSHU_RETENTION_HOURS", "72")),
            )
        except ValueError:
            self.retention_hours = 72
        self._prune_expired()

    def _job_dir(self, job_id: str) -> Path:
        return self.root / job_id

    def _record_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "job.json"

    def _write(self, job_id: str, record: dict[str, Any]) -> None:
        path = self._record_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)

    def _read(self, job_id: str) -> dict[str, Any] | None:
        path = self._record_path(job_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._prune_expired()
        job_id = uuid.uuid4().hex
        created_at = _now_iso()
        record = {
            "schema_version": "mingshu-job/1.0",
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "stage": "等待生成",
            "created_at": created_at,
            "updated_at": created_at,
            "request": payload,
            "result": None,
            "error": None,
        }
        with self._lock:
            self._write(job_id, record)
        self.executor.submit(self._run, job_id)
        return self.public(record)

    def _prune_expired(self) -> None:
        """Remove completed job bundles after the configured download window."""
        cutoff = datetime.now(UTC) - timedelta(hours=self.retention_hours)
        with self._lock:
            for job_dir in self.root.iterdir():
                if not job_dir.is_dir():
                    continue
                record = self._read(job_dir.name)
                if not record or record.get("status") not in {"succeeded", "failed"}:
                    continue
                finished = record.get("finished_at") or record.get("updated_at")
                try:
                    finished_at = datetime.fromisoformat(str(finished))
                    if finished_at.tzinfo is None:
                        finished_at = finished_at.replace(tzinfo=UTC)
                except (TypeError, ValueError):
                    continue
                if finished_at < cutoff:
                    shutil.rmtree(job_dir, ignore_errors=True)

    def _update(self, job_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            record = self._read(job_id)
            if record is None:
                raise KeyError(job_id)
            record.update(changes)
            record["updated_at"] = _now_iso()
            self._write(job_id, record)
            return record

    def _run(self, job_id: str) -> None:
        record = self._update(
            job_id,
            status="running",
            progress=2,
            stage="读取出生资料",
            started_at=_now_iso(),
        )

        def report(progress: int, stage: str) -> None:
            self._update(
                job_id,
                status="running",
                progress=max(2, min(int(progress), 99)),
                stage=str(stage),
            )

        try:
            result = self.runner(
                job_id,
                dict(record["request"]),
                self._job_dir(job_id),
                report,
            )
        except Exception as exc:  # pragma: no cover - exercised through endpoint tests
            self._update(
                job_id,
                status="failed",
                stage="生成失败",
                error={"message": str(exc)},
                finished_at=_now_iso(),
            )
            return
        self._update(
            job_id,
            status="succeeded",
            progress=100,
            stage="命书已经生成",
            result=result,
            error=None,
            finished_at=_now_iso(),
        )

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._read(job_id)
        return self.public(record) if record else None

    def wait(self, job_id: str, timeout: float = 10.0) -> dict[str, Any] | None:
        """Wait for a terminal state. Intended for tests and local tooling."""
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            record = self.get(job_id)
            if record and record["status"] in {"succeeded", "failed"}:
                return record
            time.sleep(0.02)
        return self.get(job_id)

    def download_path(self, job_id: str, kind: str) -> Path | None:
        with self._lock:
            record = self._read(job_id)
        if not record or record.get("status") != "succeeded":
            return None
        result = record.get("result") or {}
        downloads = result.get("downloads") or {}
        filename = downloads.get(kind)
        if not isinstance(filename, str) or Path(filename).name != filename:
            return None
        path = (self._job_dir(job_id) / "downloads" / filename).resolve()
        try:
            path.relative_to(self._job_dir(job_id).resolve())
        except ValueError:
            return None
        return path if path.is_file() else None

    @staticmethod
    def public(record: dict[str, Any] | None) -> dict[str, Any] | None:
        if record is None:
            return None
        payload = {
            key: record.get(key)
            for key in (
                "id",
                "status",
                "progress",
                "stage",
                "created_at",
                "updated_at",
                "started_at",
                "finished_at",
                "request",
                "result",
                "error",
            )
            if record.get(key) is not None
        }
        return payload
