from pathlib import Path

import pytest

from android_app.main import create_android_app, generate_report_from_uploads


def test_android_app_create_and_import():
    app = create_android_app()
    assert app is not None


def test_android_generator_requires_input():
    with pytest.raises(ValueError):
        generate_report_from_uploads("", "")


def test_android_generator_builds_valid_workbook(tmp_path):
    zip_path = tmp_path / "sample.zip"
    checklist_path = tmp_path / "checklist.csv"
    checklist_path.write_text(
        "Location,Item,Description,Status,Priority\nLobby,Light,Emeregency allignment,Open,High\n",
        encoding="utf-8",
    )

    import zipfile

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("chat.txt", "20/09/2026, 10:00 - Inspector: Door handle loose")

    output_path = generate_report_from_uploads(str(zip_path), str(checklist_path), correct_spelling=True)

    assert Path(output_path).exists()
    assert "Summary" in __import__("openpyxl").load_workbook(output_path).sheetnames
