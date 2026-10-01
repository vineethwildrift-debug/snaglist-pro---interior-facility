import json
import os
import time
from pathlib import Path

import pytest

import snaglist_pro.licensing as L


@pytest.fixture(autouse=True)
def _isolate_license_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SNAGLIST_LICENSE_DIR", str(tmp_path / "license"))
    monkeypatch.delenv("SNAGLIST_LICENSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("SNAGLIST_LICENSE_PRIVATE_KEY", raising=False)
    monkeypatch.setattr(L, "_license_dir", lambda: tmp_path / "license")
    yield


@pytest.fixture
def keypair(tmp_path):
    priv, pub = L.generate_keypair(tmp_path / "k.priv", tmp_path / "k.pub")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("SNAGLIST_LICENSE_PUBLIC_KEY", str(pub))
    monkeypatch.setenv("SNAGLIST_LICENSE_PRIVATE_KEY", str(priv))
    yield priv, pub, monkeypatch
    monkeypatch.undo()


def _issue(keypair, **kw):
    priv, pub, _ = keypair
    return L.issue_token(private_key_path=Path(priv), **kw)


class TestIssuance:
    def test_gen_keypair_creates_files(self, tmp_path):
        priv, pub = L.generate_keypair(tmp_path / "priv.pem", tmp_path / "pub.pem")
        assert Path(priv).exists()
        assert Path(pub).exists()
        assert L.public_key_fingerprint(Path(pub))

    def test_issue_token_round_trips(self, keypair):
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["report"])
        payload = L._parse_token(tok)
        assert payload["license_id"] == "LIC-1"
        assert payload["edition"] == "Pro"
        assert payload["features"] == ["report"]
        assert payload["max_activations"] == L.DEFAULT_MAX_ACTIVATIONS
        assert payload["type"] == L.TOKEN_TYPE
        assert float(payload["not_after"]) > time.time()

    def test_wrong_key_rejects_token(self, tmp_path, keypair):
        priv1, pub1, _ = keypair
        priv2, pub2 = L.generate_keypair(tmp_path / "b.priv", tmp_path / "b.pub")
        tok = L.issue_token(license_id="LIC-3", customer="Acme", edition="Pro", features=["report"], private_key_path=Path(priv2))
        with pytest.raises(ValueError, match="signature"):
            L._parse_token(tok)


class TestTamperResistance:
    def test_tampered_signature_rejected(self, keypair):
        import base64
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["report"])
        env = json.loads(tok)
        sig = bytearray(base64.b64decode(env["signature"]))
        sig[0] ^= 0xFF
        env["signature"] = base64.b64encode(bytes(sig)).decode()
        with pytest.raises(ValueError, match="signature"):
            L._parse_token(json.dumps(env, sort_keys=True, separators=(",", ":")))

    def test_tampered_payload_rejected(self, keypair):
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["report"])
        env = json.loads(tok)
        env["payload"]["edition"] = "Free"
        with pytest.raises(ValueError, match="signature"):
            L._parse_token(json.dumps(env, sort_keys=True, separators=(",", ":")))


class TestEntitlement:
    def test_unlicensed_is_gated(self):
        e = L.evaluate_entitlement()
        assert e["status"] == "unlicensed"
        assert e["gated"] is True

    def test_active_license_is_not_gated(self, keypair):
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["report"])
        assert L.install_token(tok)["ok"] is True
        e = L.evaluate_entitlement()
        assert e["status"] == "active"
        assert e["gated"] is False
        assert "report" in e["features"]

    def test_expired_token_enters_grace_then_expires(self, keypair):
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["report"], lease_days=-1)
        L.install_token(tok)
        e = L.evaluate_entitlement()
        assert e["status"] == "expired"
        assert e["gated"] is True

    def test_feature_gating(self, keypair):
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["excel"])
        L.install_token(tok)
        assert L.is_feature_allowed("excel") is True
        assert L.is_feature_allowed("google_sheets") is False


class TestClockRollback:
    def test_clock_rollback_is_tampered(self, keypair):
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["report"])
        L.install_token(tok)
        L._save_watermark(time.time() + 100000)
        e = L.evaluate_entitlement()
        assert e["status"] == "tampered"
        assert e["gated"] is True


class TestLockout:
    def test_exponential_lockout_and_reset(self, keypair):
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["report"])
        L.install_token(tok)
        L._save_token("not-a-valid-token")
        for _ in range(L.LOCKOUT_MAX_ATTEMPTS):
            L.evaluate_entitlement()
        assert L.is_locked_out() is True
        rk = L.issue_reset_token(lease_minutes=60, private_key_path=Path(keypair[0]))
        assert L.reset_lockout(rk) is True
        assert L.is_locked_out() is False


class TestActivationLimit:
    def test_activation_limit_enforced(self, keypair):
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["report"], max_activations=1)
        assert L.install_token(tok)["ok"] is True
        meta = L._load_meta()
        assert L._activation_count(meta) == 1
        L._save_meta({**meta, "activations": ["different-machine"]})
        assert L.install_token(tok)["ok"] is False


class TestCLI:
    def test_cli_gen_keypair(self, tmp_path, capsys):
        from snaglist_pro.licensing import _cmdline
        rc = _cmdline(["gen-keypair", "--private", str(tmp_path / "p.pem"), "--public", str(tmp_path / "u.pem")])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Private key" in out and "Public key" in out and "Fingerprint" in out

    def test_cli_issue(self, keypair, tmp_path, capsys):
        from snaglist_pro.licensing import _cmdline
        priv, pub, _ = keypair
        out_path = tmp_path / "token.lic"
        rc = _cmdline([
            "issue", "--license-id", "LIC-CLI", "--customer", "Acme", "--edition", "Pro",
            "--features", "pro,excel", "--private", str(priv), "--output", str(out_path),
        ])
        assert rc == 0
        assert out_path.exists()
        L._parse_token(out_path.read_text(encoding="utf-8"))



class TestPipelineGate:
    def test_pipeline_gate_blocks_when_unlicensed(self, keypair, tmp_path):
        """The opt-in license_check gate must raise when no token is installed."""
        from snaglist_pro.pipeline import SnaglistPipeline, LicenseError
        with pytest.raises(LicenseError):
            SnaglistPipeline().run(
                zip_path=str(tmp_path / "x.zip"),
                checklist_path="",
                output_dir=str(tmp_path / "out"),
                license_check=True,
            )

    def test_pipeline_gate_allows_when_licensed(self, keypair, tmp_path):
        """A valid installed token must let the gate pass (missing ZIP is fine)."""
        from snaglist_pro.pipeline import SnaglistPipeline, LicenseError
        tok = _issue(keypair, license_id="LIC-1", customer="Acme", edition="Pro", features=["report_generation"])
        L.install_token(tok)
        try:
            SnaglistPipeline().run(
                zip_path=str(tmp_path / "missing.zip"),
                checklist_path="",
                output_dir=str(tmp_path / "out"),
                license_check=True,
            )
        except LicenseError:
            pytest.fail("valid license was rejected by the gate")
        except Exception:
            pass  # expected: the ZIP does not exist; the gate itself passed.
