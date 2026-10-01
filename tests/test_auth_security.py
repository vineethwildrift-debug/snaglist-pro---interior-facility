import os
import tempfile

import pytest

import snaglist_pro.auth as A


@pytest.fixture(autouse=True)
def _isolate_auth(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("SNAGLIST_LICENSE_DIR", str(tmp_path / "license"))
    for var in ("SNAGLIST_APP_USERNAME", "SNAGLIST_APP_PASSWORD", "SNAGLIST_SECRET"):
        monkeypatch.delenv(var, raising=False)
    yield


class TestHashing:
    def test_hash_password_does_not_crash(self):
        digest = A.hash_password("Secret123")
        assert digest.startswith("pbkdf2_sha256$600000$")

    def test_verify_password_round_trip(self):
        digest = A.hash_password("Secret123")
        assert A.verify_password("Secret123", digest) is True
        assert A.verify_password("wrong", digest) is False


class TestPasswordChangeState:
    def test_password_change_required_lives_in_auth_json(self, tmp_path):
        A.create_initial_user("admin", "Secret123")
        assert not A.get_session_file_path().exists()
        assert A.get_auth_file_path().exists()
        assert A.require_password_change() is True
        A.set_password_change_done()
        assert A.require_password_change() is False
        A.get_session_file_path().unlink(missing_ok=True)
        assert A.require_password_change() is False


class TestSessionSigning:
    def test_session_cannot_be_edited_to_stay_alive(self):
        A.create_initial_user("admin", "Secret123")
        A.update_session_activity()
        assert A.is_session_valid() is True
        import json
        path = A.get_session_file_path()
        payload = json.loads(path.read_text())
        payload["last_activity"] = 99999999999
        payload.pop("hmac", None)
        path.write_text(json.dumps(payload))
        assert A.is_session_valid() is False


class TestLockout:
    def test_exponential_lockout(self):
        A.create_initial_user("admin", "Secret123")
        assert A.is_locked_out() is False
        for _ in range(5):
            A.verify_credentials("admin", "wrong")
        assert A.is_locked_out() is True
        assert A.verify_credentials("admin", "Secret123") is False
        A.reset_lockout()
        assert A.is_locked_out() is False
        assert A.verify_credentials("admin", "Secret123") is True
