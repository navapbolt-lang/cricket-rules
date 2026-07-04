"""Tests for agent engine components."""

from app.agent.format_router import detect_format, detect_gender, format_to_string
from app.models.types import Format, Gender
from app.agent.scenarios import get_scenario_graph


class TestFormatRouter:
    def test_detect_test_format(self):
        assert detect_format("Test match rules for LBW") == Format.TEST

    def test_detect_odi_format(self):
        assert detect_format("ODI powerplay rules") == Format.ODI

    def test_detect_t20_format(self):
        assert detect_format("T20I field restrictions") == Format.T20I

    def test_detect_all_when_ambiguous(self):
        assert detect_format("What is the LBW rule?") == Format.ALL

    def test_preferred_format_overrides(self):
        assert detect_format("some random text", Format.T20I) == Format.T20I

    def test_format_to_string(self):
        assert "Test" in format_to_string(Format.TEST)
        assert "ODI" in format_to_string(Format.ODI)

    def test_detect_gender_women(self):
        assert detect_gender("women world cup final") == Gender.WOMEN

    def test_detect_gender_men(self):
        assert detect_gender("men test match") == Gender.MEN

    def test_detect_gender_all(self):
        assert detect_gender("what is a no-ball?") == Gender.ALL

    def test_detect_gender_she(self):
        assert detect_gender("she hit the ball") == Gender.WOMEN

    def test_no_substring_confusion(self):
        assert detect_gender("women playing") == Gender.WOMEN
        assert detect_gender("men playing") == Gender.MEN


class TestScenarios:
    def test_condition_check_id_ordering(self):
        conditions = get_scenario_graph("lbw")
        ids = [c.id for c in conditions]
        assert ids == sorted(ids)

    def test_condition_has_description(self):
        conditions = get_scenario_graph("lbw")
        for c in conditions:
            assert len(c.description) > 5

    def test_condition_has_law_reference(self):
        conditions = get_scenario_graph("lbw")
        for c in conditions:
            assert c.law is not None and len(c.law) > 0
