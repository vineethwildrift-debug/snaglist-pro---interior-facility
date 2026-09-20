from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP_LAUNCHER = ROOT / "app_launcher.py"


def test_launcher_uses_native_desktop_entrypoint():
    text = APP_LAUNCHER.read_text(encoding="utf-8")
    assert "run_desktop_app" in text or "Tk" in text


def test_native_desktop_module_exists():
    native_module = ROOT / "desktop_app.py"
    assert native_module.exists()


def test_desktop_shell_uses_modern_theme():
    native_module = ROOT / "desktop_app.py"
    text = native_module.read_text(encoding="utf-8")
    assert "0f172a" in text
    assert "94a3b8" in text
    assert "modern" in text.lower()


def test_desktop_app_escapes_multiword_font_family():
    native_module = ROOT / "desktop_app.py"
    text = native_module.read_text(encoding="utf-8")
    assert 'option_add("*Font", "{Segoe UI} 10")' in text


def test_desktop_app_has_download_action():
    native_module = ROOT / "desktop_app.py"
    text = native_module.read_text(encoding="utf-8")
    assert "Download Excel/Sheets" in text
    assert "download_output" in text
    assert ".xlsx" in text
