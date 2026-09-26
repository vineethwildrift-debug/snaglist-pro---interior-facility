from pathlib import Path

from snaglist_pro.config import _build_settings


def test_default_database_url_uses_user_profile(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\demo\AppData\Local")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = _build_settings()
    database_url = settings.database_url
    assert "SnaglistPro" in database_url
    assert "Program Files" not in database_url
    assert database_url.startswith("sqlite:///C:/") or database_url.startswith("sqlite:///C:\\")
