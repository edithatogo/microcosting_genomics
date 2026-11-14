# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Tests for the scenario modeling module."""

import polars as pl
import pytest

from genomics_microcosting.scenario_modeling import (
    Scenario,
    ScenarioManager,
    create_common_scenarios,
)
from tests.checks import require_equal, require_keys, require_runtime_instance


def test_scenario_creation() -> None:
    """Test creating a scenario."""
    scenario = Scenario(
        name="test_scenario",
        description="A test scenario",
        parameters={"param1": 1.0},
        adjustments={"column1": 1.1},
    )

    if not (scenario.name == "test_scenario"):
        raise AssertionError
    if not (scenario.description == "A test scenario"):
        raise AssertionError
    if not (scenario.parameters == {"param1": 1.0}):
        raise AssertionError
    if not (scenario.adjustments == {"column1": 1.1}):
        raise AssertionError


def test_scenario_manager_creation() -> None:
    """Test creating a scenario manager."""
    # Create sample data
    sample_data = {
        "test_table": pl.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [4, 5, 6],
            },
        ),
    }

    scenario_manager = ScenarioManager(sample_data)

    if not (scenario_manager.base_data == sample_data):
        raise AssertionError
    if not (len(scenario_manager.scenarios) == 0):
        raise AssertionError
    if not (len(scenario_manager.results) == 0):
        raise AssertionError


def test_add_scenario() -> None:
    """Test adding a scenario to the manager."""
    # Create sample data
    sample_data = {
        "test_table": pl.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [4, 5, 6],
            },
        ),
    }

    scenario_manager = ScenarioManager(sample_data)

    scenario = Scenario(
        name="test_scenario",
        description="A test scenario",
        parameters={"param1": 1.0},
        adjustments={"A": 1.1},
    )

    scenario_manager.add_scenario(scenario)

    if not (len(scenario_manager.scenarios) == 1):
        raise AssertionError
    if "test_scenario" not in scenario_manager.scenarios:
        raise AssertionError
    if not (scenario_manager.scenarios["test_scenario"] == scenario):
        raise AssertionError


def test_add_scenario_from_dict() -> None:
    """Test adding a scenario from dictionary parameters."""
    # Create sample data
    sample_data = {
        "test_table": pl.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [4, 5, 6],
            },
        ),
    }

    scenario_manager = ScenarioManager(sample_data)

    scenario_manager.add_scenario_from_dict(
        name="test_scenario",
        description="A test scenario",
        parameters={"param1": 1.0},
        adjustments={"A": 1.1},
    )

    if not (len(scenario_manager.scenarios) == 1):
        raise AssertionError
    if "test_scenario" not in scenario_manager.scenarios:
        raise AssertionError

    scenario = scenario_manager.scenarios["test_scenario"]
    if not (scenario.name == "test_scenario"):
        raise AssertionError
    if not (scenario.description == "A test scenario"):
        raise AssertionError
    if not (scenario.parameters == {"param1": 1.0}):
        raise AssertionError
    if not (scenario.adjustments == {"A": 1.1}):
        raise AssertionError


def test_apply_scenario() -> None:
    """Test applying a scenario to data."""
    absolute_tolerance = 1e-10
    # Create sample data
    sample_data = {
        "test_table": pl.DataFrame(
            {
                "A": [100.0, 200.0, 300.0],
                "B": [400.0, 500.0, 600.0],
            },
        ),
    }

    scenario_manager = ScenarioManager(sample_data)

    scenario_manager.add_scenario_from_dict(
        name="inflation",
        description="10% inflation",
        parameters={"inflation_rate": 0.10},
        adjustments={"A": 1.10},
    )

    # Apply scenario
    result_df = scenario_manager.apply_scenario("inflation", "test_table")

    # Check that the scenario was applied correctly
    require_equal(len(result_df), 3)
    if not (abs(result_df["A"][0] - 110.0) < absolute_tolerance):
        raise AssertionError  # 100 * 1.10
    if not (abs(result_df["A"][1] - 220.0) < absolute_tolerance):
        raise AssertionError  # 200 * 1.10
    if not (abs(result_df["A"][2] - 330.0) < absolute_tolerance):
        raise AssertionError  # 300 * 1.10
    if not (abs(result_df["B"][0] - 400.0) < absolute_tolerance):
        raise AssertionError  # Unchanged
    if not (abs(result_df["B"][1] - 500.0) < absolute_tolerance):
        raise AssertionError  # Unchanged
    if not (abs(result_df["B"][2] - 600.0) < absolute_tolerance):
        raise AssertionError  # Unchanged


def test_apply_scenario_invalid_scenario() -> None:
    """Test applying an invalid scenario."""
    # Create sample data
    sample_data = {
        "test_table": pl.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [4, 5, 6],
            },
        ),
    }

    scenario_manager = ScenarioManager(sample_data)

    # Try to apply a scenario that doesn't exist
    with pytest.raises(ValueError, match="Scenario 'nonexistent' not found"):
        scenario_manager.apply_scenario("nonexistent", "test_table")


def test_apply_scenario_invalid_table() -> None:
    """Test applying a scenario to an invalid table."""
    # Create sample data
    sample_data = {
        "test_table": pl.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [4, 5, 6],
            },
        ),
    }

    scenario_manager = ScenarioManager(sample_data)

    scenario_manager.add_scenario_from_dict(
        name="test_scenario",
        description="A test scenario",
        parameters={},
        adjustments={"A": 1.1},
    )

    # Try to apply scenario to a table that doesn't exist
    with pytest.raises(ValueError, match="Table 'nonexistent' not found in base data"):
        scenario_manager.apply_scenario("test_scenario", "nonexistent")


def test_run_scenario_analysis() -> None:
    """Test running a scenario analysis."""
    absolute_tolerance = 1e-10
    # Create sample data
    sample_data = {
        "test_table": pl.DataFrame(
            {
                "A": [100.0, 200.0, 300.0],
                "B": [400.0, 500.0, 600.0],
            },
        ),
    }

    scenario_manager = ScenarioManager(sample_data)

    scenario_manager.add_scenario_from_dict(
        name="inflation",
        description="10% inflation",
        parameters={"inflation_rate": 0.10},
        adjustments={"A": 1.10},
    )

    # Run scenario analysis
    results = scenario_manager.run_scenario_analysis("inflation")

    # Check results
    if not (len(results) == 1):
        raise AssertionError
    if "test_table" not in results:
        raise AssertionError
    if not (len(scenario_manager.results) == 1):
        raise AssertionError
    if "inflation" not in scenario_manager.results:
        raise AssertionError

    result_df = results["test_table"]
    if not (abs(result_df["A"][0] - 110.0) < absolute_tolerance):
        raise AssertionError  # 100 * 1.10
    if not (abs(result_df["A"][1] - 220.0) < absolute_tolerance):
        raise AssertionError  # 200 * 1.10
    if not (abs(result_df["A"][2] - 330.0) < absolute_tolerance):
        raise AssertionError  # 300 * 1.10


def test_compare_scenarios() -> None:
    """Test comparing scenarios."""
    expected_comparison_rows = 2
    expected_a_baseline = 600.0
    expected_a_inflation_10 = 660.0
    expected_a_inflation_20 = 720.0
    expected_b_cost = 1500.0
    # Create sample data
    sample_data = {
        "test_table": pl.DataFrame(
            {
                "A": [100.0, 200.0, 300.0],
                "B": [400.0, 500.0, 600.0],
            },
        ),
    }

    scenario_manager = ScenarioManager(sample_data)

    # Add scenarios
    scenario_manager.add_scenario_from_dict(
        name="inflation_10",
        description="10% inflation",
        parameters={"inflation_rate": 0.10},
        adjustments={"A": 1.10},
    )

    scenario_manager.add_scenario_from_dict(
        name="inflation_20",
        description="20% inflation",
        parameters={"inflation_rate": 0.20},
        adjustments={"A": 1.20},
    )

    # Compare scenarios
    comparison_df = scenario_manager.compare_scenarios(
        ["inflation_10", "inflation_20"],
        "test_table",
    )

    # Check comparison results
    require_equal(
        len(comparison_df),
        expected_comparison_rows,
    )  # Two numeric columns (A and B)
    require_keys(comparison_df.columns, ("Column",))
    require_keys(comparison_df.columns, ("Base Case",))
    require_keys(comparison_df.columns, ("inflation_10",))
    require_keys(comparison_df.columns, ("inflation_20",))

    # Check values for column A
    a_row = comparison_df.filter(pl.col("Column") == "A").row(0, named=True)
    require_equal(a_row["Base Case"], expected_a_baseline)  # 100 + 200 + 300
    require_equal(a_row["inflation_10"], expected_a_inflation_10)  # 110 + 220 + 330
    require_equal(a_row["inflation_20"], expected_a_inflation_20)  # 120 + 240 + 360

    # Check values for column B (unchanged)
    b_row = comparison_df.filter(pl.col("Column") == "B").row(0, named=True)
    require_equal(b_row["Base Case"], expected_b_cost)  # 400 + 500 + 600
    require_equal(b_row["inflation_10"], expected_b_cost)  # Unchanged
    require_equal(b_row["inflation_20"], expected_b_cost)  # Unchanged


def test_create_common_scenarios() -> None:
    """Test creating common scenarios."""
    scenarios = create_common_scenarios()

    # Check that we have the expected scenarios
    expected_scenarios = [
        "inflation_5",
        "cost_reduction_10",
        "high_throughput",
        "labor_cost_increase",
    ]

    for scenario_name in expected_scenarios:
        if scenario_name not in scenarios:
            raise AssertionError
        require_runtime_instance(scenarios[scenario_name], Scenario)

    # Check specific scenario details
    inflation_scenario = scenarios["inflation_5"]
    if not (inflation_scenario.name == "inflation_5"):
        raise AssertionError
    if "5% inflation" not in inflation_scenario.description:
        raise AssertionError
    if "unit_cost_aud_per_unit" not in inflation_scenario.adjustments:
        raise AssertionError
    require_equal(inflation_scenario.adjustments["unit_cost_aud_per_unit"], 1.05)


if __name__ == "__main__":
    pytest.main([__file__])
