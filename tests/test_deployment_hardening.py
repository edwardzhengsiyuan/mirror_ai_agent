"""Deployment boundary regressions using disposable files and synthetic secrets."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from cryptography.fernet import Fernet, InvalidToken
import pytest

from agent.billing import BillingStore
from agent.storage.locking import ProfileLease, ProfileBusyError, profile_lock_path
from agent.storage.profile_store import edit_profile, save_profile, load_profile


def test_portal_keys_are_encrypted_and_wrong_secret_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("BILLING_KEY_ENCRYPTION_KEYS", raising=False)
    path = str(tmp_path / "billing.db")
    store = BillingStore(path, app_secret="stable-test-secret")
    store.create_user("u")
    plaintext, key_hash = store.issue_api_key("u", store_plaintext=True)
    with closing(store._connect()) as conn:
        row = conn.execute("SELECT plaintext, ciphertext FROM api_keys").fetchone()
    assert row["plaintext"] is None
    assert row["ciphertext"] != plaintext
    assert plaintext not in json.dumps(store.list_api_keys("u"))
    assert store.lookup_api_key(plaintext)["user_id"] == "u"
    assert BillingStore(path, app_secret="stable-test-secret").get_current_user_api_key("u")["plaintext"] == plaintext
    with pytest.raises(InvalidToken):
        BillingStore(path, app_secret="wrong-secret")
    assert store.get_current_user_api_key("u")["plaintext"] == plaintext
    store.revoke_api_key(key_hash)
    with closing(store._connect()) as conn:
        assert conn.execute("SELECT ciphertext FROM api_keys").fetchone()[0] is None


def test_legacy_key_migration_backup_and_rotation(tmp_path, monkeypatch, capsys):
    from scripts.secure_billing_keys import main
    key1, key2 = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    monkeypatch.setenv("BILLING_KEY_ENCRYPTION_KEYS", key1)
    path = tmp_path / "billing.db"
    store = BillingStore(str(path))
    store.create_user("u")
    plaintext, key_hash = store.issue_api_key("u")
    with store.transaction() as conn:
        conn.execute("UPDATE api_keys SET plaintext = ? WHERE api_key_hash = ?", (plaintext, key_hash))
    backup = tmp_path / "before.db"
    assert main(["--db", str(path), "--backup", str(backup), "--service-stopped"]) == 0
    assert json.loads(capsys.readouterr().out)["plaintext_rows"] == 0
    assert plaintext.encode() not in path.read_bytes()
    assert plaintext.encode() in backup.read_bytes()
    monkeypatch.setenv("BILLING_KEY_ENCRYPTION_KEYS", key2 + "," + key1)
    rotated = BillingStore(str(path))
    assert rotated.migrate_api_key_storage(rotate=True) == 1
    monkeypatch.setenv("BILLING_KEY_ENCRYPTION_KEYS", key2)
    assert BillingStore(str(path)).get_current_user_api_key("u")["plaintext"] == plaintext
    monkeypatch.setenv("BILLING_KEY_ENCRYPTION_KEYS", key1)
    with pytest.raises(InvalidToken):
        BillingStore(str(path))


def test_portal_key_requires_stable_encryption_material(tmp_path, monkeypatch):
    monkeypatch.delenv("BILLING_KEY_ENCRYPTION_KEYS", raising=False)
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)
    store = BillingStore(str(tmp_path / "billing.db"))
    store.create_user("u")
    with pytest.raises(ValueError, match="require"):
        store.issue_api_key("u", store_plaintext=True)
    assert store.list_api_keys("u") == []


def test_ciphertext_cannot_be_swapped_between_api_key_rows(tmp_path):
    store = BillingStore(str(tmp_path / "billing.db"), app_secret="test-secret")
    store.create_user("a")
    store.create_user("b")
    store.issue_api_key("a", store_plaintext=True)
    store.issue_api_key("b", store_plaintext=True)
    with store.transaction() as conn:
        conn.execute("UPDATE api_keys SET ciphertext = (SELECT ciphertext FROM api_keys WHERE user_id = 'b') WHERE user_id = 'a'")
    with pytest.raises(ValueError, match="integrity"):
        store.get_current_user_api_key("a")


def test_edit_profile_rollback_and_cli_share_lock(tmp_path):
    path = str(tmp_path / "profile.json")
    save_profile(path, {"value": "old"})
    with pytest.raises(RuntimeError):
        with edit_profile(path) as profile:
            profile["value"] = "discard"
            raise RuntimeError("failed computation")
    assert load_profile(path) == {"value": "old"}
    with ProfileLease(profile_lock_path(path)):
        with pytest.raises(ProfileBusyError):
            with edit_profile(path):
                pass
        result = subprocess.run([sys.executable, "app.py", "--profile", path, "--question", "test"], capture_output=True)
        assert result.returncode != 0
        assert b"ProfileBusyError" in result.stderr
    with edit_profile(path) as profile:
        profile["value"] = "new"
    assert load_profile(path)["value"] == "new"


def test_retention_preview_preserves_active_profiles_and_recent_logs(tmp_path):
    from scripts.prune_conversations import prune
    user = tmp_path / "users" / "u"
    logs = user / "conversations"
    logs.mkdir(parents=True)
    old, recent = logs / "old.jsonl", logs / "recent.jsonl"
    old.write_text("old")
    recent.write_text("new")
    old_time = time.time() - 100 * 86400
    os.utime(old, (old_time, old_time))
    assert len(prune(tmp_path)["eligible"]) == 1
    assert old.exists()
    with ProfileLease(profile_lock_path(user / "profile.json")):
        assert prune(tmp_path, apply=True)["deleted"] == []
    result = prune(tmp_path, apply=True)
    assert len(result["deleted"]) == 1
    assert recent.exists() and not old.exists()


def test_frontend_assets_match_manifest_and_are_local():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "web/vendor/manifest.json").read_text())
    page = (root / "web/app.html").read_text(encoding="utf-8")
    for item in manifest:
        assert hashlib.sha256((root / "web/vendor" / item["file"]).read_bytes()).hexdigest() == item["sha256"]
        assert 'src="/vendor/' + item["file"] + '"' in page
        assert item["sri"] in page
    assert '<script src="https://' not in page


def test_image_excludes_sensitive_local_artifacts():
    root = Path(__file__).resolve().parents[1]
    patterns = set((root / ".dockerignore").read_text(encoding="utf-8").splitlines())
    assert {".env", ".deploy.env", ".tmp", "storage", "*.db", "*vouchers*.csv", "*vouchers*.md"} <= patterns


def test_abrupt_process_exit_releases_lease_and_leaves_recoverable_charge(tmp_path, monkeypatch, capsys):
    from scripts.reconcile_billing import main
    monkeypatch.delenv("BILLING_KEY_ENCRYPTION_KEYS", raising=False)
    path, profile = tmp_path / "billing.db", tmp_path / "profile.json"
    script = """
import os, sys
from agent.billing import BillingStore, BillingService
from agent.storage.locking import ProfileLease, profile_lock_path
lease = ProfileLease(profile_lock_path(sys.argv[2]))
service = BillingService(BillingStore(sys.argv[1]))
service.create_user('interrupted', initial_credits=100)
service.charge('interrupted', '/v1/ask', 20, request_id='interrupted-request')
os._exit(7)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path), str(profile)], capture_output=True)
    assert result.returncode == 7, result.stderr
    with ProfileLease(profile_lock_path(profile)):
        pass
    store = BillingStore(str(path))
    assert store.list_pending_charges()[0]["request_id"] == "interrupted-request"
    assert main(["--db", str(path), "--action", "refund", "--request-id", "interrupted-request",
                 "--reason", "Verified process exited before execution", "--service-stopped"]) == 0
    assert store.get_user("interrupted")["balance_credits"] == 100
    assert store.list_pending_charges() == []


def test_retention_never_follows_external_symlink(tmp_path):
    from scripts.prune_conversations import prune
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "old.jsonl"
    secret.write_text("preserve")
    old_time = time.time() - 100 * 86400
    os.utime(secret, (old_time, old_time))
    root = tmp_path / "storage"
    user = root / "users/u"
    user.mkdir(parents=True)
    try:
        (user / "conversations").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires privileges on this Windows host")
    result = prune(root, apply=True)
    assert result["deleted"] == []
    assert secret.read_text() == "preserve"
