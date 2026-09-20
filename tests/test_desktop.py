from pathlib import Path

from snaglist_pro.web.app import get_app_data_dir


def test_app_data_dir_is_in_user_profile():
    data_dir = get_app_data_dir()
    assert isinstance(data_dir, Path)
    assert "SnaglistPro" in data_dir.name or "snaglistpro" in data_dir.name.lower()
    assert str(data_dir).lower().find("appdata") != -1 or str(data_dir).lower().find("local") != -1
