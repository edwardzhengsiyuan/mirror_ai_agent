"""Host backup permissions and rejection before pruning; synthetic SQLite only."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest


@pytest.mark.skipif(os.name == "nt" or shutil.which("bash") is None,
                    reason="POSIX host backup wrapper requires Bash")
def test_backup_is_private_and_invalid_retention_preserves_files(tmp_path):
    db = tmp_path / "source.db"
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE audit(value TEXT)")
    connection.execute("INSERT INTO audit VALUES ('synthetic')")
    connection.commit()
    connection.close()
    tools = tmp_path / "bin"
    tools.mkdir()
    sqlite = tools / "sqlite3"
    sqlite.write_text(f"#!{sys.executable}\n" +
        "import sqlite3,sys\n"
        "src=sqlite3.connect(sys.argv[1]); dst=sqlite3.connect(sys.argv[2][9:-1])\n"
        "src.backup(dst); dst.close(); src.close()\n")
    sqlite.chmod(0o700)
    reports = tmp_path / "backups"
    env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"],
               BILLING_DB=str(db), BACKUP_DIR=str(reports), RETENTION_DAYS="30")
    script = Path(__file__).resolve().parents[1] / "scripts/backup_billing.sh"
    old_mask = os.umask(0o022)
    try:
        subprocess.run(["bash", str(script)], env=env, check=True)
    finally:
        os.umask(old_mask)
    snapshots = list(reports.glob("billing-*"))
    assert len(snapshots) == 1
    assert snapshots[0].stat().st_mode & 0o077 == 0
    original = snapshots[0].read_bytes()
    env["RETENTION_DAYS"] = "-1"
    assert subprocess.run(["bash", str(script)], env=env).returncode == 2
    assert snapshots[0].read_bytes() == original
