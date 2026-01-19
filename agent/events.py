"""Event helpers for streaming execution updates."""

from __future__ import annotations

import datetime as dt
import threading
from typing import Any, Callable, Dict, Optional

Event = Dict[str, Any]
EventSink = Callable[[Event], None]

_EMIT_LOCK = threading.Lock()


def emit_event(sink: Optional[EventSink], event: Event) -> None:
    """Safely emit an event to the sink if provided."""
    if sink is None:
        return
    if "ts" not in event:
        event["ts"] = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
    with _EMIT_LOCK:
        sink(event)


def emit_text_chunks(text: str, on_delta: Callable[[str], None], chunk_size: int = 200) -> None:
    """Emit text in chunks to simulate streaming output."""
    if not text:
        return
    for idx in range(0, len(text), chunk_size):
        on_delta(text[idx : idx + chunk_size])
