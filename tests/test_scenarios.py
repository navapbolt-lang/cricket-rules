"""Tests for scenario graphs and condition checks."""

from app.agent.scenarios import get_scenario_graph
from app.models.types import ScenarioType


class TestScenarioGraphs:
    def test_lbw_graph_has_conditions(self):
        conditions = get_scenario_graph("lbw")
        assert len(conditions) >= 3
        assert conditions[0].law == "36.1"
        assert "pitch" in conditions[0].description.lower()

    def test_lbw_terminal_condition_first(self):
        conditions = get_scenario_graph("lbw")
        assert conditions[0].terminal is True

    def test_drs_graph_has_conditions(self):
        conditions = get_scenario_graph("drs_review")
        assert len(conditions) >= 2
        assert any("umpire" in c.description.lower() for c in conditions)

    def test_run_out_graph(self):
        conditions = get_scenario_graph("run_out")
        assert len(conditions) >= 2
        assert any("ground" in c.description.lower() for c in conditions)

    def test_stumping_graph(self):
        conditions = get_scenario_graph("stumping")
        assert len(conditions) >= 2

    def test_no_ball_graph(self):
        conditions = get_scenario_graph("no_ball")
        assert len(conditions) >= 2
        assert any("front foot" in c.description.lower() for c in conditions)

    def test_wide_ball_graph(self):
        conditions = get_scenario_graph("wide")
        assert len(conditions) >= 2

    def test_boundary_catch_graph(self):
        conditions = get_scenario_graph("boundary_catch")
        assert len(conditions) >= 2

    def test_invalid_scenario_returns_fallback(self):
        conditions = get_scenario_graph("invalid_type")
        assert len(conditions) == 1
        assert "pre-defined conditions" in conditions[0].description.lower()

    def test_all_scenario_types_exist(self):
        for scenario in ScenarioType:
            conditions = get_scenario_graph(scenario.value)
            if scenario == ScenarioType.DLS:
                continue
            assert isinstance(conditions, list)
