"""Tests for the scenario modeling module."""

import pandas as pd
import pytest
from pathlib import Path

from unimelb_phd_phase_1.scenario_modeling import Scenario, ScenarioManager, create_common_scenarios


def test_scenario_creation():
    """Test creating a scenario."""
    scenario = Scenario(
        name="test_scenario",
        description="A test scenario",
        parameters={"param1": 1.0},
        adjustments={"column1": 1.1}
    )
    
    assert scenario.name == "test_scenario"
    assert scenario.description == "A test scenario"
    assert scenario.parameters == {"param1": 1.0}
    assert scenario.adjustments == {"column1": 1.1}


def test_scenario_manager_creation():
    """Test creating a scenario manager."""
    # Create sample data
    sample_data = {
        "test_table": pd.DataFrame({
            "A": [1, 2, 3],
            "B": [4, 5, 6]
        })
    }
    
    scenario_manager = ScenarioManager(sample_data)
    
    assert scenario_manager.base_data == sample_data
    assert len(scenario_manager.scenarios) == 0
    assert len(scenario_manager.results) == 0


def test_add_scenario():
    """Test adding a scenario to the manager."""
    # Create sample data
    sample_data = {
        "test_table": pd.DataFrame({
            "A": [1, 2, 3],
            "B": [4, 5, 6]
        })
    }
    
    scenario_manager = ScenarioManager(sample_data)
    
    scenario = Scenario(
        name="test_scenario",
        description="A test scenario",
        parameters={"param1": 1.0},
        adjustments={"A": 1.1}
    )
    
    scenario_manager.add_scenario(scenario)
    
    assert len(scenario_manager.scenarios) == 1
    assert "test_scenario" in scenario_manager.scenarios
    assert scenario_manager.scenarios["test_scenario"] == scenario


def test_add_scenario_from_dict():
    """Test adding a scenario from dictionary parameters."""
    # Create sample data
    sample_data = {
        "test_table": pd.DataFrame({
            "A": [1, 2, 3],
            "B": [4, 5, 6]
        })
    }
    
    scenario_manager = ScenarioManager(sample_data)
    
    scenario_manager.add_scenario_from_dict(
        name="test_scenario",
        description="A test scenario",
        parameters={"param1": 1.0},
        adjustments={"A": 1.1}
    )
    
    assert len(scenario_manager.scenarios) == 1
    assert "test_scenario" in scenario_manager.scenarios
    
    scenario = scenario_manager.scenarios["test_scenario"]
    assert scenario.name == "test_scenario"
    assert scenario.description == "A test scenario"
    assert scenario.parameters == {"param1": 1.0}
    assert scenario.adjustments == {"A": 1.1}


def test_apply_scenario():
    """Test applying a scenario to data."""
    # Create sample data
    sample_data = {
        "test_table": pd.DataFrame({
            "A": [100.0, 200.0, 300.0],
            "B": [400.0, 500.0, 600.0]
        })
    }
    
    scenario_manager = ScenarioManager(sample_data)
    
    scenario_manager.add_scenario_from_dict(
        name="inflation",
        description="10% inflation",
        parameters={"inflation_rate": 0.10},
        adjustments={"A": 1.10}
    )
    
    # Apply scenario
    result_df = scenario_manager.apply_scenario("inflation", "test_table")
    
    # Check that the scenario was applied correctly
    assert len(result_df) == 3
    assert abs(result_df["A"].iloc[0] - 110.0) < 1e-10  # 100 * 1.10
    assert abs(result_df["A"].iloc[1] - 220.0) < 1e-10  # 200 * 1.10
    assert abs(result_df["A"].iloc[2] - 330.0) < 1e-10  # 300 * 1.10
    assert abs(result_df["B"].iloc[0] - 400.0) < 1e-10  # Unchanged
    assert abs(result_df["B"].iloc[1] - 500.0) < 1e-10  # Unchanged
    assert abs(result_df["B"].iloc[2] - 600.0) < 1e-10  # Unchanged


def test_apply_scenario_invalid_scenario():
    """Test applying an invalid scenario."""
    # Create sample data
    sample_data = {
        "test_table": pd.DataFrame({
            "A": [1, 2, 3],
            "B": [4, 5, 6]
        })
    }
    
    scenario_manager = ScenarioManager(sample_data)
    
    # Try to apply a scenario that doesn't exist
    with pytest.raises(ValueError, match="Scenario 'nonexistent' not found"):
        scenario_manager.apply_scenario("nonexistent", "test_table")


def test_apply_scenario_invalid_table():
    """Test applying a scenario to an invalid table."""
    # Create sample data
    sample_data = {
        "test_table": pd.DataFrame({
            "A": [1, 2, 3],
            "B": [4, 5, 6]
        })
    }
    
    scenario_manager = ScenarioManager(sample_data)
    
    scenario_manager.add_scenario_from_dict(
        name="test_scenario",
        description="A test scenario",
        parameters={},
        adjustments={"A": 1.1}
    )
    
    # Try to apply scenario to a table that doesn't exist
    with pytest.raises(ValueError, match="Table 'nonexistent' not found in base data"):
        scenario_manager.apply_scenario("test_scenario", "nonexistent")


def test_run_scenario_analysis():
    """Test running a scenario analysis."""
    # Create sample data
    sample_data = {
        "test_table": pd.DataFrame({
            "A": [100.0, 200.0, 300.0],
            "B": [400.0, 500.0, 600.0]
        })
    }
    
    scenario_manager = ScenarioManager(sample_data)
    
    scenario_manager.add_scenario_from_dict(
        name="inflation",
        description="10% inflation",
        parameters={"inflation_rate": 0.10},
        adjustments={"A": 1.10}
    )
    
    # Run scenario analysis
    results = scenario_manager.run_scenario_analysis("inflation")
    
    # Check results
    assert len(results) == 1
    assert "test_table" in results
    assert len(scenario_manager.results) == 1
    assert "inflation" in scenario_manager.results
    
    result_df = results["test_table"]
    assert abs(result_df["A"].iloc[0] - 110.0) < 1e-10  # 100 * 1.10
    assert abs(result_df["A"].iloc[1] - 220.0) < 1e-10  # 200 * 1.10
    assert abs(result_df["A"].iloc[2] - 330.0) < 1e-10  # 300 * 1.10


def test_compare_scenarios():
    """Test comparing scenarios."""
    # Create sample data
    sample_data = {
        "test_table": pd.DataFrame({
            "A": [100.0, 200.0, 300.0],
            "B": [400.0, 500.0, 600.0]
        })
    }
    
    scenario_manager = ScenarioManager(sample_data)
    
    # Add scenarios
    scenario_manager.add_scenario_from_dict(
        name="inflation_10",
        description="10% inflation",
        parameters={"inflation_rate": 0.10},
        adjustments={"A": 1.10}
    )
    
    scenario_manager.add_scenario_from_dict(
        name="inflation_20",
        description="20% inflation",
        parameters={"inflation_rate": 0.20},
        adjustments={"A": 1.20}
    )
    
    # Compare scenarios
    comparison_df = scenario_manager.compare_scenarios(
        ["inflation_10", "inflation_20"], 
        "test_table"
    )
    
    # Check comparison results
    assert len(comparison_df) == 2  # Two numeric columns (A and B)
    assert "Column" in comparison_df.columns
    assert "Base Case" in comparison_df.columns
    assert "inflation_10" in comparison_df.columns
    assert "inflation_20" in comparison_df.columns
    
    # Check values for column A
    a_row = comparison_df[comparison_df["Column"] == "A"].iloc[0]
    assert a_row["Base Case"] == 600.0  # 100 + 200 + 300
    assert a_row["inflation_10"] == 660.0  # 110 + 220 + 330
    assert a_row["inflation_20"] == 720.0  # 120 + 240 + 360
    
    # Check values for column B (unchanged)
    b_row = comparison_df[comparison_df["Column"] == "B"].iloc[0]
    assert b_row["Base Case"] == 1500.0  # 400 + 500 + 600
    assert b_row["inflation_10"] == 1500.0  # Unchanged
    assert b_row["inflation_20"] == 1500.0  # Unchanged


def test_create_common_scenarios():
    """Test creating common scenarios."""
    scenarios = create_common_scenarios()
    
    # Check that we have the expected scenarios
    expected_scenarios = [
        "inflation_5",
        "cost_reduction_10",
        "high_throughput",
        "labor_cost_increase"
    ]
    
    for scenario_name in expected_scenarios:
        assert scenario_name in scenarios
        assert isinstance(scenarios[scenario_name], Scenario)
        
    # Check specific scenario details
    inflation_scenario = scenarios["inflation_5"]
    assert inflation_scenario.name == "inflation_5"
    assert "5% inflation" in inflation_scenario.description
    assert "Unit Cost" in inflation_scenario.adjustments
    assert inflation_scenario.adjustments["Unit Cost"] == 1.05


if __name__ == "__main__":
    pytest.main([__file__])