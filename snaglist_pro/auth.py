import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Optional, Tuple

# PBKDF2-HMAC-SHA256 iteration count. OWASP recommends 600,000 for
# PBKDF2-HMAC-SHA256; Argon2id is preferred but kept optional so the module
# still imports when argon2-cffi is not installed.
_PASSWORD_ITERATIONS = int(os.environ.get("SNAGLIST_PASSWORD_ITERATIONS", "600000"))

# Idle session timeout in seconds (30 minutes).
_SESSION_TIMEOUT = 1800
_SESSION_FILE = "session.json"


def _app_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "SnaglistPro"
    return Path.home() / ".snaglistpro"


def get_auth_file_path() -> Path:
    return _app_data_dir() / "auth.json"


def get_secret_file_path() -> Path:
    return _app_data_dir() / "secret"


def get_session_file_path() -> Path:
    return _app_data_dir() / _SESSION_FILE


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        _PASSWORD_ITERATIONS,
    )
    return f"pbkdf2_sha256${_PASSWORD_ITERATIONS}${salt_bytes.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_text)
        expected = bytes.fromhex(digest_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def _check_password_complexity(password: str) -> Tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    return True, ""


def create_initial_user(username: str, password: str) -> bool:
    username = (username or "").strip()
    if len(username) < 3 or len(username) > 100:
        return False
    ok, msg = _check_password_complexity(password)
    if not ok:
        return False

    path = get_auth_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "username": username,
        "password_hash": hash_password(password),
    }
    try:
        with open(path, "x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        if os.name != "nt":
            os.chmod(path, 0o600)
        return True
    except FileExistsError:
        return False


def _credentials_from_environment() -> Optional[Tuple[str, str]]:
    username = os.environ.get("SNAGLIST_APP_USERNAME", "").strip()
    password = os.environ.get("SNAGLIST_APP_PASSWORD", "")
    if username and password:
        return username, hash_password(password)
    return None


def get_configured_user() -> Optional[Tuple[str, str]]:
    environment_user = _credentials_from_environment()
    if environment_user:
        return environment_user

    path = get_auth_file_path()
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        username = str(payload.get("username", "")).strip()
        password_hash = str(payload.get("password_hash", "")).strip()
        if username and password_hash:
            return username, password_hash
    except (OSError, ValueError, TypeError):
        return None
    return None


def has_configured_credentials() -> bool:
    return get_configured_user() is not None


def verify_credentials(username: str, password: str) -> bool:
    if is_locked_out():
        return False
    configured = get_configured_user()
    if configured is None:
        return False
    configured_username, password_hash = configured
    ok = (
        hmac.compare_digest(configured_username, (username or "").strip())
        and verify_password(password, password_hash)
    )
    if ok:
        _save_attempt_state({"count": 0, "first_at": 0.0, "locked_until": 0.0})
        return True
    state = _load_attempt_state()
    count = int(state.get("count", 0) or 0) + 1
    state["count"] = count
    if not state.get("first_at"):
        state["first_at"] = time.time()
    state["locked_until"] = time.time() + _lockout_seconds(count)
    _save_attempt_state(state)
    return False


def _session_hmac(secret: str, body: str) -> str:
    return hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


def is_session_valid() -> bool:
    path = get_session_file_path()
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        last_activity = payload.get("last_activity", 0)
        if time.time() - last_activity > _SESSION_TIMEOUT:
            path.unlink(missing_ok=True)
            return False
        # Verify the HMAC so the session cannot be edited to stay alive.
        body = json.dumps(
            {"last_activity": last_activity, "user": payload.get("user", "")},
            sort_keys=True,
            separators=(",", ":"),
        )
        expected = _session_hmac(get_or_create_secret(), body)
        if not hmac.compare_digest(str(payload.get("hmac", "")), expected):
            path.unlink(missing_ok=True)
            return False
        return True
    except Exception:
        return False


def update_session_activity():
    path = get_session_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        user = get_configured_user()[0] if get_configured_user() else ""
        last_activity = time.time()
        body = json.dumps(
            {"last_activity": last_activity, "user": user},
            sort_keys=True,
            separators=(",", ":"),
        )
        session = {
            "last_activity": last_activity,
            "user": user,
            "hmac": _session_hmac(get_or_create_secret(), body),
        }
        path.write_text(json.dumps(session), encoding="utf-8")
    except Exception:
        pass


def require_password_change() -> bool:
    """Whether the operator must change the initial password on next login.

    Stored in auth.json, not the ephemeral session file, so it survives the
    30-minute idle timeout and cannot be reset by deleting session.json.
    """
    path = get_auth_file_path()
    if not path.exists():
        return True
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        return bool(payload.get("password_change_required", True))
    except Exception:
        return True


def set_password_change_done():
    path = get_auth_file_path()
    try:
        if not path.exists():
            return
        with open(path, "r+", encoding="utf-8") as handle:
            payload = json.load(handle)
            payload["password_change_required"] = False
            handle.seek(0)
            handle.truncate()
            json.dump(payload, handle, indent=2)
    except Exception:
        pass


def _load_attempt_state() -> dict:
    path = get_secret_file_path().with_suffix(".attempts")
    if not path.exists():
        return {"count": 0, "first_at": 0.0, "locked_until": 0.0}
    try:
        with open(path, encoding="utf-8") as handle:
            parsed = json.load(handle)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {"count": 0, "first_at": 0.0, "locked_until": 0.0}


def _save_attempt_state(state: dict) -> None:
    path = get_secret_file_path().with_suffix(".attempts")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        if os.name != "nt":
            os.chmod(path, 0o600)
    except Exception:
        pass


def is_locked_out() -> bool:
    state = _load_attempt_state()
    locked_until = float(state.get("locked_until", 0.0) or 0.0)
    return time.time() < locked_until


def _lockout_seconds(count: int) -> float:
    # Exponential backoff: 30s, 60s, 120s, 240s, 480s, capped at 15 minutes.
    if count <= 0:
        return 0.0
    seconds = 30 * (2 ** (count - 1))
    return min(seconds, 15 * 60)


def reset_lockout() -> bool:
    _save_attempt_state({"count": 0, "first_at": 0.0, "locked_until": 0.0})
    return True


def get_or_create_secret() -> str:
    environment_secret = os.environ.get("SNAGLIST_SECRET", "").strip()
    if environment_secret:
        return environment_secret

    path = get_secret_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "x", encoding="utf-8") as handle:
            secret = secrets.token_urlsafe(48)
            handle.write(secret)
        if os.name != "nt":
            os.chmod(path, 0o600)
        return secret
    except FileExistsError:
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return secrets.token_urlsafe(48)
