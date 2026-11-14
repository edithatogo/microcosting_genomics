# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Native plugin and scenario invariants, independent of study data."""

import math
lazy from pathlib import Path

import polars as pl
import pytest
from matplotlib.patches import Rectangle
from polars.testing import assert_frame_equal

from genomics_microcosting.advanced_scenario_modeling import (
    AdvancedScenario,
    AdvancedScenarioManager,
)
from genomics_microcosting.advanced_visualization import plot_cost_trend_analysis
from genomics_microcosting.plugins.enhanced_cost_analysis import (
    EnhancedCostAnalysisPlugin,
)
from genomics_microcosting.plugins.example_cost_analysis import CostAnalysisPlugin
from genomics_microcosting.plugins.sample_enhanced_plugin import (
    SampleCostAnalysisPlugin,
)
from tests.checks import require_equal


def test_plugins_preserve_nulls_ids_and_sample_statistics() -> None:
    """Missing values are excluded temporarily and original values retained."""
    frame = pl.DataFrame(
        {"id": ["001", "002", "003", "004"], "cost": [1.0, 3.0, None, float("nan")]},
    )
    original = frame.clone()
    for plugin in (CostAnalysisPlugin(), EnhancedCostAnalysisPlugin()):
        result = (
            plugin.analyze(frame, detailed=True)
            if isinstance(plugin, EnhancedCostAnalysisPlugin)
            else plugin.analyze(frame)
        )
        if not (result["numeric_columns"] == 1):
            raise AssertionError
        require_equal(result["cost_statistics"]["mean_cost"]["cost"], 2.0)
        if not (
            result["cost_statistics"]["std_cost"]["cost"]
            == pytest.approx(
                math.sqrt(2),
            )
        ):
            raise AssertionError
        if not (result["memory_usage_mb"] == frame.estimated_size() / 1024**2):
            raise AssertionError
    require_equal(SampleCostAnalysisPlugin().analyze(frame)["rows"], 4)
    assert_frame_equal(frame, original)
    if not (
        "cost_statistics"
        not in CostAnalysisPlugin().analyze(
            pl.DataFrame({"id": ["001"]}),
        )
    ):
        raise AssertionError
    if (
        CostAnalysisPlugin().analyze(pl.DataFrame({"cost": [1.0]}))["cost_statistics"][
            "std_cost"
        ]["cost"]
        is not None
    ):
        raise AssertionError


def test_advanced_scenarios_quantiles_exports_and_registration(tmp_path: Path) -> None:
    """Perturbations run and exports retain explicit metric labels."""
    frame = pl.DataFrame(
        {"id": ["001", "002", "003", "004"], "cost": [1.0, 2.0, 3.0, 4.0]},
    )
    manager = AdvancedScenarioManager({"table": frame})
    manager.add_advanced_scenario(
        AdvancedScenario(
            "double",
            "Synthetic",
            {},
            {"cost": 2.0},
            probability_distributions={
                "cost": {"type": "uniform", "low": 2.0, "high": 2.0},
            },
        ),
    )
    manager.run_scenario_analysis("double")
    summary = manager.compare_scenarios_detailed(["double"], "table")["cost"]
    require_equal(
        summary.filter(pl.col("Metric") == "25th Percentile")["Base Case"][0],
        1.75,
    )
    require_equal(summary.filter(pl.col("Metric") == "Mean")["double"][0], 5.0)
    sensitivity = manager.run_sensitivity_analysis(
        "double",
        "cost",
        2.0,
        3.0,
        steps=2,
    )["results"]
    if not isinstance(sensitivity, dict) or sensitivity["table"] != [20.0, 30.0]:
        raise AssertionError
    draws = manager.run_probabilistic_analysis("double", iterations=2)
    require_equal(len(draws), 2)
    require_equal(draws[0]["table"]["cost"].sum(), 20.0)
    manager.export_scenario_results(
        "double",
        str(tmp_path),
        formats=["csv", "json", "parquet"],
    )
    assert_frame_equal(
        pl.read_parquet(tmp_path / "parquet/double_table.parquet"),
        manager.results["double"]["table"],
    )
    assert_frame_equal(
        frame,
        pl.DataFrame(
            {"id": ["001", "002", "003", "004"], "cost": [1.0, 2.0, 3.0, 4.0]},
        ),
    )


def test_tornado_chart_uses_unregistered_perturbations() -> None:
    """Plot the largest change while retaining only the registered scenario."""
    manager = AdvancedScenarioManager({"table": pl.DataFrame({"cost": [4.0, 6.0]})})
    manager.add_advanced_scenario(AdvancedScenario("base", "Synthetic", {}, {}))

    chart = manager.generate_tornado_chart(
        "base",
        "table",
        {"cost": (2.0, 3.0)},
        "cost",
    )

    bar = chart.axes[0].patches[0]
    if not isinstance(bar, Rectangle) or bar.get_width() != pytest.approx(20.0):
        pytest.fail("Expected a maximum change of 20 from the baseline total of 10")
    if tuple(manager.scenarios) != ("base",):
        pytest.fail("Chart generation changed the registered scenarios")


def test_cost_trend_labels_include_singleton_groups() -> None:
    """Render labels from the same deviations used by the error bars."""
    data = pl.DataFrame({"category": ["a", "a", "b"], "cost": [1.0, 3.0, 4.0]})
    figure = plot_cost_trend_analysis(data, "category", "cost")
    require_equal([label.get_text() for label in figure.axes[0].texts], ["n=2", "n=1"])
