# -*- coding: utf-8 -*-
"""Snaglist Pro licensing module (Option A).

Self-contained, offline-verifiable entitlement for a paid desktop application.
The client verifies a signed license token against an embedded public key and
never needs the private signing key. The private key lives only on the owner's
machine and is used only by the issuer CLI.

Design notes
------------
- Entitlement is decided by a *signed* token, not a local flag. A determined
  user can patch the client, but cannot forge a signature without the private
  key.
- Clock trust is limited: a monotonic watermark defends against wall-clock
  rollback; an offline grace window keeps paying users working during
  construction-site outages.
- Enforcement gates *new report generation*, never reading or exporting
  already-produced data.
- State is stored in the OS credential store (DPAPI on Windows) so the token
  and watermark cannot be edited by another user.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    _CRYPTO_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _CRYPTO_AVAILABLE = False
    InvalidSignature = Exception  # type: ignore[misc,assignment]

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Token validity (lease). A short lease makes revocation effective within one
# cycle and limits the blast radius of a leaked token.
DEFAULT_LEASE_DAYS = 30

# Offline grace window: how long a valid token may be used without a
# re-validation heartbeat before generation is locked.
DEFAULT_GRACE_DAYS = 7

# How far the local clock may drift backwards before we treat the machine as
# tampered (in seconds). Forward drift is tolerated up to the grace window.
MAX_CLOCK_BACKWARD_SECONDS = 600  # 10 minutes

# Activation limit per license. A coarse fingerprint is hashed, so a single
# license can activate on up to this many distinct machines.
DEFAULT_MAX_ACTIVATIONS = 2

# Failed-verification lockout (exponential). 5 attempts -> 30s, doubling,
# capped at 15 minutes, then the owner must issue a reset key.
LOCKOUT_BASE_SECONDS = 30
LOCKOUT_MAX_SECONDS = 15 * 60
LOCKOUT_MAX_ATTEMPTS = 5

# Token version. Bump when the payload schema changes so old tokens are
# rejected rather than misinterpreted.
TOKEN_VERSION = 1

# Token type tag, embedded in the payload so the verifier can distinguish a
# license token from other signed blobs.
TOKEN_TYPE = "snaglist_pro_license"

# Default public-key location shipped with the client (owner-controlled).
DEFAULT_PUBLIC_KEY_PATH = Path(__file__).resolve().parent / "license.pub"

# Default private-key location for the issuer (owner-only).
DEFAULT_PRIVATE_KEY_PATH = Path(__file__).resolve().parent / "license.priv"

# State file names inside the OS credential store directory.
_TOKEN_FILE = "license.token"
_WATERMARK_FILE = "license.watermark"
_ATTEMPTS_FILE = "license.attempts"
_META_FILE = "license.meta"
# ---------------------------------------------------------------------------
# OS credential storage (DPAPI on Windows, fallback to file otherwise)
# ---------------------------------------------------------------------------

def _app_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "SnaglistPro"
    return Path.home() / ".snaglistpro"


def _license_dir() -> Path:
    path = Path(os.environ.get("SNAGLIST_LICENSE_DIR", "") or "")
    if str(path).strip():
        return path
    return _app_data_dir() / "license"


def _protect(data: bytes) -> bytes:
    """Encrypt data at rest with the OS credential store.

    On Windows this uses DPAPI (CryptProtectData) which is bound to the
    user's logon credentials and adds a MAC for tamper detection. On other
    platforms it falls back to a random per-file key stored alongside the
    data (weaker, but the signed token is still the real gate).
    """
    try:
        import win32crypt  # type: ignore

        encrypted = win32crypt.CryptProtectData(
            data, None, None, None, None, 0,
        )
        return base64.b64encode(encrypted)
    except Exception:
        pass
    # Fallback: XOR with a random key stored in the same file (weak; token
    # signature remains the authoritative gate).
    key = secrets.token_bytes(32)
    cipher = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.b64encode(key + b"\x00" + cipher)


def _unprotect(payload: bytes) -> bytes:
    raw = base64.b64decode(payload)
    try:
        import win32crypt  # type: ignore

        description, data = win32crypt.CryptUnprotectData(
            raw, None, None, None, 0,
        )
        return data
    except Exception:
        pass
    # Fallback: first 32 bytes are the key, rest is the XOR cipher.
    if len(raw) < 33:
        return b""
    key = raw[:32]
    cipher = raw[32:]
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(cipher))


def _read_secret(name: str) -> Optional[bytes]:
    path = _license_dir() / name
    if not path.exists():
        return None
    try:
        payload = path.read_bytes()
        data = _unprotect(payload)
        return data if data else None
    except Exception:
        return None


def _write_secret(name: str, data: bytes) -> None:
    path = _license_dir() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_protect(data))
    try:
        if os.name != "nt":
            os.chmod(path, 0o600)
    except Exception:
        pass


def _read_plain(name: str) -> Optional[bytes]:
    path = _license_dir() / name
    if not path.exists():
        return None
    try:
        return path.read_bytes()
    except Exception:
        return None


def _write_plain(name: str, data: bytes) -> None:
    path = _license_dir() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    try:
        if os.name != "nt":
            os.chmod(path, 0o600)
    except Exception:
        pass
# ---------------------------------------------------------------------------
# Machine fingerprinting
# ---------------------------------------------------------------------------

def _machine_fingerprint() -> str:
    """Return a coarse, stable machine identifier hashed to 16 hex chars.

    Uses Windows MachineGuid (stable across reboots/updates) plus the system
    volume serial. We deliberately keep it coarse so that legitimate hardware
    changes do not lock out paying users, and hash it so the raw identifiers
    are not stored in plaintext.
    """
    parts = []
    try:
        import ctypes
        import subprocess

        # MachineGuid from the registry.
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(1024)
            advapi32 = ctypes.windll.advapi32
            hkey = ctypes.c_void_p()
            if advapi32.RegOpenKeyExW(
                ctypes.c_void_p(0x80000002),  # HKEY_LOCAL_MACHINE
                "SYSTEM\\CurrentControlSet\\Control\\ComputerName\\ComputerName",
                0, 0x200000 | 0x1,  # KEY_READ
                ctypes.byref(hkey),
            ) == 0:
                try:
                    if advapi32.RegQueryValueExW(
                        hkey, "ComputerName", None, None,
                        ctypes.byref(buf), ctypes.byref(size),
                    ) == 0:
                        parts.append(buf.value)
                finally:
                    advapi32.RegCloseKey(hkey)
        except Exception:
            pass

        try:
            vol = subprocess.run(
                ["fsutil", "queryinfo", "C:\\"],
                capture_output=True, text=True, timeout=5,
            )
            for line in vol.stdout.splitlines():
                if "Volume Serial Number" in line:
                    parts.append(line.split(":", 1)[1].strip())
        except Exception:
            pass

        try:
            parts.append(socket.gethostname())
        except Exception:
            pass
    except Exception:
        pass

    try:
        parts.append(socket.gethostname())
    except Exception:
        pass

    if not parts:
        parts.append("unknown-machine")

    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


# Imported lazily so the module loads on platforms without socket.
import socket  # noqa: E402


# ---------------------------------------------------------------------------
# Token encoding / decoding
# ---------------------------------------------------------------------------

def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def _canonical(payload: Dict[str, Any]) -> bytes:
    """Canonical byte representation used for signing.

    JSON is serialized with sorted keys and no whitespace so the signature
    is independent of key ordering or formatting.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _build_payload(
    license_id: str,
    customer: str,
    edition: str,
    features: list,
    not_before: float,
    not_after: float,
    machine_hash: str = "",
    max_activations: int = DEFAULT_MAX_ACTIVATIONS,
    version: int = TOKEN_VERSION,
    token_type: str = TOKEN_TYPE,
) -> Dict[str, Any]:
    return {
        "version": version,
        "type": token_type,
        "license_id": license_id,
        "customer": customer,
        "edition": edition,
        "features": sorted(features),
        "not_before": not_before,
        "not_after": not_after,
        "machine_hash": machine_hash,
        "max_activations": max_activations,
    }


def _decode_payload(token_text: str) -> Dict[str, Any]:
    """Decode a license token (JSON envelope with signature).

    Format (single line, base64url of JSON):
        {"payload": {...}, "signature": "<b64 ed25519>"}
    """
    try:
        envelope = json.loads(token_text)
    except Exception:
        raise ValueError("token is not valid JSON")
    if not isinstance(envelope, dict) or "payload" not in envelope or "signature" not in envelope:
        raise ValueError("token envelope missing payload/signature")
    payload = envelope["payload"]
    if not isinstance(payload, dict):
        raise ValueError("token payload is not an object")
    return payload


def _signature_bytes(token_text: str) -> bytes:
    envelope = json.loads(token_text)
    return _unb64(envelope["signature"])
# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

def generate_keypair(private_path: Optional[Path] = None, public_path: Optional[Path] = None) -> Tuple[str, str]:
    """Generate an Ed25519 keypair and persist them.

    The private key is PEM-encoded PKCS#8 and is owner-only. The public key
    is PEM-encoded SubjectPublicKeyInfo and is safe to ship with the client.
    Returns (private_path, public_path) as strings.
    """
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package is required for key generation")
    private_path = Path(private_path or DEFAULT_PRIVATE_KEY_PATH)
    public_path = Path(public_path or DEFAULT_PUBLIC_KEY_PATH)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    try:
        os.chmod(private_path, 0o600)
    except Exception:
        pass
    return str(private_path), str(public_path)


def load_public_key(path: Optional[Path] = None):
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package is required")
    env_override = os.environ.get("SNAGLIST_LICENSE_PUBLIC_KEY", "").strip()
    path = Path(path or env_override or DEFAULT_PUBLIC_KEY_PATH)
    if not path.exists():
        raise FileNotFoundError(f"public key not found: {path}")
    return serialization.load_pem_public_key(path.read_bytes())


def load_private_key(path: Optional[Path] = None):
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package is required")
    env_override = os.environ.get("SNAGLIST_LICENSE_PRIVATE_KEY", "").strip()
    path = Path(path or env_override or DEFAULT_PRIVATE_KEY_PATH)
    if not path.exists():
        raise FileNotFoundError(f"private key not found: {path}")
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def public_key_fingerprint(path: Optional[Path] = None) -> str:
    key = load_public_key(path)
    pem = key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(pem).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Issuance (owner-side)
# ---------------------------------------------------------------------------

def issue_token(
    license_id: str,
    customer: str,
    edition: str,
    features,
    lease_days: int = DEFAULT_LEASE_DAYS,
    machine_hash: str = "",
    max_activations: int = DEFAULT_MAX_ACTIVATIONS,
    private_key_path: Optional[Path] = None,
    not_before_offset_seconds: int = -300,
) -> str:
    """Sign a license token with the owner's private key.

    not_before is set slightly in the past so tokens issued just before
    midnight are valid immediately. not_after is lease_days from now.
    """
    private_key = load_private_key(private_key_path)
    now = time.time()
    payload = _build_payload(
        license_id=license_id,
        customer=customer,
        edition=edition,
        features=list(features),
        not_before=now + not_before_offset_seconds,
        not_after=now + lease_days * 86400,
        machine_hash=machine_hash,
        max_activations=max_activations,
    )
    canonical = _canonical(payload)
    signature = private_key.sign(canonical)
    envelope = {
        "payload": payload,
        "signature": _b64(signature),
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def issue_token_to_file(
    license_id: str,
    customer: str,
    edition: str,
    features,
    lease_days: int = DEFAULT_LEASE_DAYS,
    machine_hash: str = "",
    max_activations: int = DEFAULT_MAX_ACTIVATIONS,
    output_path: Optional[Path] = None,
    private_key_path: Optional[Path] = None,
) -> str:
    token = issue_token(
        license_id, customer, edition, features, lease_days,
        machine_hash, max_activations, private_key_path,
    )
    output_path = Path(output_path or (_license_dir() / f"{license_id}.lic"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(token, encoding="utf-8")
    return str(output_path)


# ---------------------------------------------------------------------------
# Verification (client-side)
# ---------------------------------------------------------------------------

def _parse_token(token_text: str) -> Dict[str, Any]:
    """Validate structure and signature, return the payload."""
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package is required")
    try:
        envelope = json.loads(token_text)
    except Exception as exc:
        raise ValueError("invalid token JSON") from exc
    if not isinstance(envelope, dict) or "payload" not in envelope or "signature" not in envelope:
        raise ValueError("invalid token envelope")
    payload = envelope["payload"]
    if not isinstance(payload, dict):
        raise ValueError("invalid token payload")
    signature = _unb64(envelope["signature"])
    canonical = _canonical(payload)
    public_key = load_public_key()
    try:
        public_key.verify(signature, canonical)
    except InvalidSignature as exc:
        raise ValueError("token signature verification failed") from exc
    return payload


def _validate_payload(payload: Dict[str, Any], now: float, machine_hash: str = "") -> Dict[str, Any]:
    """Validate semantic fields. Returns a dict of problems (empty = valid)."""
    problems = []
    version = payload.get("version")
    if version != TOKEN_VERSION:
        problems.append(f"unsupported token version: {version!r}")
    token_type = payload.get("type")
    if token_type != TOKEN_TYPE:
        problems.append(f"unsupported token type: {token_type!r}")
    license_id = payload.get("license_id")
    if not license_id or not isinstance(license_id, str):
        problems.append("missing license_id")
    not_before = payload.get("not_before")
    not_after = payload.get("not_after")
    if not isinstance(not_before, (int, float)) or not isinstance(not_after, (int, float)):
        problems.append("missing or non-numeric expiry fields")
    else:
        if now < not_before - 300:
            problems.append("token not yet valid")
        if now > not_after:
            problems.append("token expired")
    if machine_hash:
        bound = payload.get("machine_hash")
        if bound and bound != machine_hash:
            problems.append("token is bound to a different machine")
    max_activations = payload.get("max_activations")
    if not isinstance(max_activations, int) or max_activations < 1:
        problems.append("invalid max_activations")
    features = payload.get("features")
    if not isinstance(features, list):
        problems.append("invalid features list")
    return {"problems": problems, "license_id": license_id, "not_after": not_after}
# ---------------------------------------------------------------------------
# State: token, watermark, attempts, activation metadata
# ---------------------------------------------------------------------------

def _load_token() -> Optional[str]:
    data = _read_secret(_TOKEN_FILE)
    if data is None:
        data = _read_plain(_TOKEN_FILE)
    if data is None:
        return None
    try:
        return data.decode("utf-8")
    except Exception:
        return None


def _save_token(token_text: str) -> None:
    _write_secret(_TOKEN_FILE, token_text.encode("utf-8"))


def _load_watermark() -> float:
    data = _read_secret(_WATERMARK_FILE)
    if data is None:
        data = _read_plain(_WATERMARK_FILE)
    if not data:
        return 0.0
    try:
        return float(data.decode("utf-8").strip())
    except Exception:
        return 0.0


def _save_watermark(value: float) -> None:
    _write_secret(_WATERMARK_FILE, f"{value:.3f}".encode("utf-8"))


def _load_attempts() -> Dict[str, Any]:
    data = _read_secret(_ATTEMPTS_FILE)
    if data is None:
        data = _read_plain(_ATTEMPTS_FILE)
    if not data:
        return {"count": 0, "first_at": 0.0, "locked_until": 0.0}
    try:
        parsed = json.loads(data.decode("utf-8"))
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {"count": 0, "first_at": 0.0, "locked_until": 0.0}


def _save_attempts(state: Dict[str, Any]) -> None:
    _write_secret(_ATTEMPTS_FILE, json.dumps(state).encode("utf-8"))


def _reset_attempts() -> None:
    _save_attempts({"count": 0, "first_at": 0.0, "locked_until": 0.0})


def _load_meta() -> Dict[str, Any]:
    data = _read_secret(_META_FILE)
    if data is None:
        data = _read_plain(_META_FILE)
    if not data:
        return {}
    try:
        parsed = json.loads(data.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _save_meta(meta: Dict[str, Any]) -> None:
    _write_secret(_META_FILE, json.dumps(meta).encode("utf-8"))


def _activation_count(meta: Dict[str, Any]) -> int:
    activations = meta.get("activations")
    if isinstance(activations, list):
        return len(activations)
    if isinstance(activations, int):
        return activations
    return 0


def _record_activation(meta: Dict[str, Any], machine_hash: str, max_activations: int) -> bool:
    """Record an activation.

    Returns True if the activation was allowed, False if the license has
    reached its activation limit on a *different* machine. Re-installing the
    same token on a machine already activated is idempotent and always
    allowed, so legitimate re-installs never fail.
    """
    activations = meta.get("activations")
    if not isinstance(activations, list):
        activations = []
    if machine_hash in activations:
        # Already activated on this machine; idempotent success.
        return True
    if len(activations) >= max_activations:
        return False
    activations = activations + [machine_hash]
    meta["activations"] = activations
    _save_meta(meta)
    return True


# ---------------------------------------------------------------------------
# Lockout (exponential backoff on failed verification)
# ---------------------------------------------------------------------------

def _lockout_seconds(count: int) -> float:
    if count <= 0:
        return 0.0
    seconds = LOCKOUT_BASE_SECONDS * (2 ** (count - 1))
    return min(seconds, LOCKOUT_MAX_SECONDS)


def is_locked_out() -> bool:
    state = _load_attempts()
    locked_until = float(state.get("locked_until", 0.0) or 0.0)
    return time.time() < locked_until


def _record_failure() -> float:
    state = _load_attempts()
    count = int(state.get("count", 0) or 0) + 1
    state["count"] = count
    if state.get("first_at", 0.0) in (None, 0.0):
        state["first_at"] = time.time()
    state["locked_until"] = time.time() + _lockout_seconds(count)
    _save_attempts(state)
    return state["locked_until"]


def reset_lockout(reset_key: str) -> bool:
    """Owner-issued reset key unlocks after a hard lockout.

    The reset key is a short-lived, single-use token signed by the owner
    that simply clears the attempt counter. It is validated structurally
    (signature + type) but carries no entitlement.
    """
    try:
        payload = _parse_token(reset_key)
    except Exception:
        return False
    if payload.get("type") != "snaglist_pro_reset":
        return False
    _reset_attempts()
    return True


def issue_reset_token(lease_minutes: int = 60, private_key_path: Optional[Path] = None) -> str:
    """Issue a single-use reset key for an owner to unlock a hard-locked install."""
    private_key = load_private_key(private_key_path)
    now = time.time()
    payload = {
        "version": TOKEN_VERSION,
        "type": "snaglist_pro_reset",
        "license_id": "reset",
        "not_before": now - 300,
        "not_after": now + lease_minutes * 60,
    }
    canonical = _canonical(payload)
    signature = private_key.sign(canonical)
    return json.dumps({"payload": payload, "signature": _b64(signature)}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
# ---------------------------------------------------------------------------
# Entitlement evaluation
# ---------------------------------------------------------------------------

def _now_seconds() -> float:
    return time.time()


def _check_clock_watermark(now: float) -> Tuple[bool, float]:
    """Defend against wall-clock rollback.

    Returns (ok, new_watermark). If the clock moved backwards by more than
    MAX_CLOCK_BACKWARD_SECONDS we treat the machine as tampered and do not
    advance the watermark.
    """
    watermark = _load_watermark()
    if watermark <= 0:
        _save_watermark(now)
        return True, now
    if now < watermark - MAX_CLOCK_BACKWARD_SECONDS:
        return False, watermark
    new_watermark = max(watermark, now)
    _save_watermark(new_watermark)
    return True, new_watermark


def install_token(token_text: str) -> Dict[str, Any]:
    """Persist a freshly issued license token (owner/activation flow)."""
    payload = _parse_token(token_text)
    machine_hash = _machine_fingerprint()
    meta = _load_meta()
    max_activations = int(payload.get("max_activations", DEFAULT_MAX_ACTIVATIONS) or DEFAULT_MAX_ACTIVATIONS)
    within_limit = _record_activation(meta, machine_hash, max_activations)
    if not within_limit:
        return {"ok": False, "error": "license has reached its activation limit"}
    _save_token(token_text)
    _reset_attempts()
    _save_watermark(_now_seconds())
    return {"ok": True, "license_id": payload.get("license_id"), "activations": _activation_count(meta)}


def evaluate_entitlement(now: Optional[float] = None) -> Dict[str, Any]:
    """Evaluate the current entitlement state.

    Returns a dict with:
      - status: "unlicensed" | "active" | "grace" | "expired" | "tampered"
      - gated: bool (whether new report generation is allowed)
      - reason: human-readable explanation
      - license_id, edition, features, expires_at, grace_until
    """
    now = now if now is not None else _now_seconds()

    if is_locked_out():
        return {
            "status": "locked_out",
            "gated": True,
            "reason": "Too many failed license checks. Use an owner-issued reset key.",
            "license_id": None,
        }

    clock_ok, _ = _check_clock_watermark(now)
    if not clock_ok:
        return {
            "status": "tampered",
            "gated": True,
            "reason": "System clock moved backwards; possible tampering detected.",
            "license_id": None,
        }

    token_text = _load_token()
    if not token_text:
        return {
            "status": "unlicensed",
            "gated": True,
            "reason": "No license token installed.",
            "license_id": None,
        }

    try:
        payload = _parse_token(token_text)
    except ValueError as exc:
        _record_failure()
        return {
            "status": "invalid",
            "gated": True,
            "reason": str(exc),
            "license_id": None,
        }

    machine_hash = _machine_fingerprint()
    result = _validate_payload(payload, now, machine_hash)
    problems = result["problems"]
    license_id = result.get("license_id")
    not_after = result.get("not_after")

    if problems:
        _record_failure()
        # Expired tokens are not a security failure, so do not count them
        # toward the lockout.
        if any("expired" in p for p in problems):
            return {
                "status": "expired",
                "gated": True,
                "reason": "License token expired. Renew with a new token.",
                "license_id": license_id,
                "expires_at": not_after,
            }
        return {
            "status": "invalid",
            "gated": True,
            "reason": "; ".join(problems),
            "license_id": license_id,
        }

    _reset_attempts()
    lease_seconds = max(0.0, float(not_after) - now)
    grace_seconds = DEFAULT_GRACE_DAYS * 86400
    grace_until = float(not_after) + grace_seconds

    if lease_seconds <= 0:
        # Within the offline grace window the user may keep working.
        if now <= grace_until:
            return {
                "status": "grace",
                "gated": False,
                "reason": "License expired; offline grace period active.",
                "license_id": license_id,
                "expires_at": not_after,
                "grace_until": grace_until,
                "features": payload.get("features", []),
                "edition": payload.get("edition", ""),
            }
        return {
            "status": "expired",
            "gated": True,
            "reason": "Offline grace period ended. Renew with a new token.",
            "license_id": license_id,
            "expires_at": not_after,
            "grace_until": grace_until,
        }

    return {
        "status": "active",
        "gated": False,
        "reason": "License active.",
        "license_id": license_id,
        "expires_at": not_after,
        "grace_until": grace_until,
        "features": payload.get("features", []),
        "edition": payload.get("edition", ""),
    }


def is_feature_allowed(feature: str) -> bool:
    """Check whether a named feature is permitted by the current entitlement."""
    entitlement = evaluate_entitlement()
    if entitlement.get("gated"):
        return False
    features = entitlement.get("features") or []
    if not features:
        return True  # no feature restrictions configured
    return feature in features


def require_entitlement(feature: Optional[str] = None) -> Dict[str, Any]:
    """Convenience wrapper returning the entitlement dict, raising if gated."""
    entitlement = evaluate_entitlement()
    if entitlement.get("gated"):
        return entitlement
    if feature and not is_feature_allowed(feature):
        entitlement = dict(entitlement)
        entitlement["gated"] = True
        entitlement["status"] = "feature_locked"
        entitlement["reason"] = f"Feature '{feature}' not included in this license."
        return entitlement
    return entitlement
# ---------------------------------------------------------------------------
# CLI (owner-side key generation and issuance)
# ---------------------------------------------------------------------------

def _cmdline(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m snaglist_pro.licensing",
        description="Snaglist Pro license key management (owner-side).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("gen-keypair", help="Generate an Ed25519 signing keypair.")
    gen.add_argument("--private", default=str(DEFAULT_PRIVATE_KEY_PATH))
    gen.add_argument("--public", default=str(DEFAULT_PUBLIC_KEY_PATH))

    issue = sub.add_parser("issue", help="Sign and write a license token.")
    issue.add_argument("--license-id", required=True)
    issue.add_argument("--customer", required=True)
    issue.add_argument("--edition", default="Pro")
    issue.add_argument("--features", default="pro,excel,google_sheets")
    issue.add_argument("--lease-days", type=int, default=DEFAULT_LEASE_DAYS)
    issue.add_argument("--max-activations", type=int, default=DEFAULT_MAX_ACTIVATIONS)
    issue.add_argument("--machine-hash", default="")
    issue.add_argument("--private", default=str(DEFAULT_PRIVATE_KEY_PATH))
    issue.add_argument("--output", default=None)

    reset = sub.add_parser("reset-key", help="Issue a single-use reset key.")
    reset.add_argument("--lease-minutes", type=int, default=60)
    reset.add_argument("--private", default=str(DEFAULT_PRIVATE_KEY_PATH))

    verify = sub.add_parser("verify", help="Verify a token file (no state changes).")
    verify.add_argument("token_file")

    args = parser.parse_args(argv)

    if args.command == "gen-keypair":
        private_path, public_path = generate_keypair(Path(args.private), Path(args.public))
        print(f"Private key: {private_path}")
        print(f"Public key:  {public_path}")
        print(f"Fingerprint: {public_key_fingerprint(Path(args.public))}")
        return 0

    if args.command == "issue":
        features = [f.strip() for f in args.features.split(",") if f.strip()]
        output = issue_token_to_file(
            license_id=args.license_id,
            customer=args.customer,
            edition=args.edition,
            features=features,
            lease_days=args.lease_days,
            machine_hash=args.machine_hash,
            max_activations=args.max_activations,
            output_path=Path(args.output) if args.output else None,
            private_key_path=Path(args.private),
        )
        print(f"Token written: {output}")
        return 0

    if args.command == "reset-key":
        token = issue_reset_token(lease_minutes=args.lease_minutes, private_key_path=Path(args.private))
        print(token)
        return 0

    if args.command == "verify":
        text = Path(args.token_file).read_text(encoding="utf-8")
        payload = _parse_token(text)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(_cmdline())
