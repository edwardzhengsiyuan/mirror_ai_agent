"""Exercise the host scheduler wrapper without Docker or production data."""
import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.skipif(os.name == "nt", reason="Linux production host wrapper")
def test_scheduled_preview_preserves_report_on_failure(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$ARGS_FILE"\n'
                      'if [ "$FAIL" = 1 ]; then echo partial; exit 7; fi\n'
                      'echo \'{"apply":false,"deleted":[]}\'\n')
    docker.chmod(0o700)
    report_dir = tmp_path / "reports"
    args_file = tmp_path / "args"
    env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ["PATH"],
               RETENTION_REPORT_DIR=str(report_dir), ARGS_FILE=str(args_file), FAIL="0",
               CONVERSATION_RETENTION_DAYS="90", RETENTION_CONTAINER="test-api")
    script = Path(__file__).resolve().parents[1] / "scripts/check_conversation_retention.sh"
    subprocess.run(["bash", str(script)], env=env, check=True)
    report = report_dir / "latest.json"
    assert json.loads(report.read_text()) == {"apply": False, "deleted": []}
    assert args_file.read_text().splitlines() == [
        "exec", "test-api", "python", "/app/scripts/prune_conversations.py",
        "--storage", "/app/storage", "--days", "90"]
    assert report.stat().st_mode & 0o077 == 0
    original = report.read_bytes()
    env["FAIL"] = "1"
    assert subprocess.run(["bash", str(script)], env=env).returncode == 7
    assert report.read_bytes() == original
    assert list(report_dir.glob(".preview.*")) == []
    env["CONVERSATION_RETENTION_DAYS"] = "0"
    assert subprocess.run(["bash", str(script)], env=env).returncode == 2
    assert report.read_bytes() == original
