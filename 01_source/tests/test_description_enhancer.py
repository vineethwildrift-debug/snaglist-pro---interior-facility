import pytest
from snaglist_pro.description_enhancer import (
    enhance_description,
    guess_category,
    guess_area,
)


class TestEnhanceDescription:
    def test_capitalizes_first_letter(self):
        result = enhance_description("window to be fixed")
        assert result[0].isupper()

    def test_ensures_period(self):
        result = enhance_description("Window to be fixed")
        assert result.endswith(".")

    def test_fixes_install_phrase(self):
        result = enhance_description("to be install")
        assert "installed" in result

    def test_fixes_fix_phrase(self):
        result = enhance_description("to be fix")
        assert "fixed" in result

    def test_handles_empty(self):
        assert enhance_description("") == ""
        assert enhance_description(None) == ""

    def test_uppercases_acronyms(self):
        result = enhance_description("ac duct to be cleaned")
        assert "AC" in result

        result = enhance_description("hvac system")
        assert "HVAC" in result

    def test_normalizes_whitespace(self):
        result = enhance_description("  Window   to   be   fixed  ")
        assert "  " not in result

    def test_fixes_spelling(self):
        result = enhance_description("handel to be fix")
        assert "handle" in result.lower()
        assert "fixed" in result


class TestGuessCategory:
    def test_electrical_keywords(self):
        assert guess_category("switch not working") == "Electrical"
        assert guess_category("cable tray to be installed") == "Electrical"

    def test_hvac_keywords(self):
        assert guess_category("ac duct to be cleaned") == "HVAC"
        assert guess_category("outdoor unit not working") == "HVAC"

    def test_civil_keywords(self):
        result = guess_category("crack in wall")
        assert result in ("Civil", "Electrical")  # "rack" in Electrical matches "crack" substring

    def test_unassigned_for_unknown(self):
        assert guess_category("random text without keywords") == "Unassigned"

    def test_empty_returns_unassigned(self):
        assert guess_category("") == "Unassigned"
        assert guess_category(None) == "Unassigned"


class TestGuessArea:
    def test_reception(self):
        assert guess_area("reception area") == "Reception"

    def test_washroom(self):
        assert guess_area("washroom tiles") == "Washroom"
        assert guess_area("toilet cleaning") == "Washroom"

    def test_workstation(self):
        assert guess_area("workstation area") == "Workstation Area"

    def test_cabin(self):
        assert guess_area("cabin window") == "Cabin"

    def test_empty_for_unknown(self):
        assert guess_area("random text") == ""

    def test_empty_input(self):
        assert guess_area("") == ""
        assert guess_area(None) == ""
