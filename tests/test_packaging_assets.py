from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "SnaglistPro.spec"


def test_pyinstaller_spec_includes_web_assets():
    text = SPEC.read_text(encoding="utf-8")
    assert "snaglist_pro/web/templates" in text
    assert "snaglist_pro/web/static" in text
