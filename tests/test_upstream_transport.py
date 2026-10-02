"""Exercise real HTTP transport failure paths without contacting model providers."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
import types

import pytest

from agent.tools import llm_tool


@pytest.mark.parametrize("behavior", ["http_error", "timeout", "invalid_json"])
def test_upstream_transport_failure_is_bounded_and_reported(behavior, monkeypatch):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.headers.get("Authorization"))
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if behavior == "timeout":
                time.sleep(0.2)
                return
            self.send_response(503 if behavior == "http_error" else 200)
            self.end_headers()
            self.wfile.write(b"not valid JSON")

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(llm_tool, "time", types.SimpleNamespace(sleep=lambda _: None))
    events = []
    started = time.monotonic()
    try:
        content, reasoning, error = llm_tool._do_llm_api_call(
            f"http://127.0.0.1:{server.server_port}/chat/completions", "synthetic-secret",
            "test-model", "system", "user", 0.05, 1, False, None, events.append, "TEST")
        assert content is None and reasoning is None and error is not None
        assert received == ["Bearer synthetic-secret"]
        assert time.monotonic() - started < 3
        assert "synthetic-secret" not in str(events)
        if behavior != "invalid_json":
            assert any(event["type"] == "llm_error" for event in events)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
