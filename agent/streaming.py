"""Bounded, nonblocking SSE delivery; slow clients never block model workers."""
from collections import deque
import json
import queue
import threading
import time


class EventBuffer:
    def __init__(self, max_events=256, max_bytes=2 * 1024 * 1024):
        self.max_events = max_events
        self.max_bytes = max_bytes
        self._events = deque()
        self._bytes = 0
        self._condition = threading.Condition()
        self._closed = False

    def put(self, event):
        with self._condition:
            if self._closed:
                return
            size = len(json.dumps(event, ensure_ascii=False).encode("utf-8"))
            if len(self._events) >= self.max_events or self._bytes + size > self.max_bytes:
                self._events.clear()
                self._bytes = 0
                self._events.append(({"type": "error", "code": "stream_overflow",
                                      "message": "Stream consumer is too slow. Processing continues in the background."}, 0))
                self._closed = True
            else:
                self._events.append((event, size))
                self._bytes += size
                if event is None:
                    self._closed = True
            self._condition.notify_all()

    def get(self, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while not self._events:
                if self._closed:
                    return None
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise queue.Empty
                self._condition.wait(remaining)
            event, size = self._events.popleft()
            self._bytes -= size
            return event

    def close(self):
        with self._condition:
            self._closed = True
            self._events.clear()
            self._bytes = 0
            self._condition.notify_all()


def sse_events(buffer, initial=(), heartbeat_seconds=15):
    try:
        for event in initial:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        while True:
            try:
                event = buffer.get(timeout=heartbeat_seconds)
            except queue.Empty:
                yield ": heartbeat\n\n"
                continue
            if event is None:
                return
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    finally:
        buffer.close()
