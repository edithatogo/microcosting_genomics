# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Native management, optimisation, rendering and export contracts."""

import io
from http import HTTPStatus
from unittest.mock import patch
lazy from collections.abc import Iterable
lazy from pathlib import Path

import matplotlib.pyplot as plt
import openpyxl
import polars as pl
import pytest
from matplotlib.patches import Rectangle
from openpyxl.worksheet.worksheet import Worksheet
from polars.testing import assert_frame_equal
lazy from matplotlib.patches import Patch

from genomics_microcosting.advanced_visualization import (
    plot_cost_boxplot,
    plot_cost_correlation_matrix,
    plot_interactive_category_costs,
    plot_interactive_cost_distribution,
)
from genomics_microcosting.data_management import DataManager
from genomics_microcosting.performance import DataOptimizer, ParallelProcessor
from genomics_microcosting.visualization import plot_category_costs, plot_cost_breakdown
from genomics_microcosting.web import create_app
from tests.checks import require_equal


def test_optimisation_preserves_identifiers_and_parallel_order() -> None:
    """Only explicitly declared strings may become numbers; callbacks conserve rows."""
    frame = pl.DataFrame({"id": ["001", "002", "003"], "x": [1, 2, 3]})
    result = DataOptimizer.optimize_dataframe(frame)
    if not (result["id"].to_list() == ["001", "002", "003"]):
        raise AssertionError
    if not (result["x"].to_list() == [1, 2, 3]):
        raise AssertionError
    if not (
        ParallelProcessor.parallel_apply(
            frame,
            lambda values: values * 2,
            "x",
            n_cores=2,
        ).to_list()
        == [2, 4, 6]
    ):
        raise AssertionError
    with pytest.raises(ValueError, match="row count"):
        ParallelProcessor.parallel_apply(
            frame,
            lambda values: values.head(0),
            "x",
            n_cores=2,
        )
    with pytest.raises(ValueError, match="positive"):
        ParallelProcessor.parallel_apply(frame, lambda values: values, "x", n_cores=0)


def test_csv_defaults_preserve_ids_and_explicit_schema(tmp_path: Path) -> None:
    """CSV lacks types; preserve text until its schema is declared."""
    path = tmp_path / "source.csv"
    path.write_text("id,cost\n001,1.50\n002,2.50\n")
    manager = DataManager(tmp_path)
    manager.register_dataset(path)
    if not (manager.load_dataset("source")["id"].to_list() == ["001", "002"]):
        raise AssertionError
    table = manager.load_dataset("source", schema_overrides={"cost": pl.Float64()})
    require_equal(table["cost"].sum(), 4.0)
    if not (table["id"].to_list() == ["001", "002"]):
        raise AssertionError


def test_category_figures_show_source_totals() -> None:
    """Native figures and interactive traces use the same conserved totals."""
    frame = pl.DataFrame(
        {
            "Category": ["B", "A", "A"],
            "cost": [3.0, 1.0, 4.0],
            "other": [1.0, 2.0, 3.0],
        },
    )
    fig = plot_category_costs(frame, "Category", "cost")
    require_equal(_rectangle_heights(fig.axes[0].patches), [5.0, 3.0])
    plt.close(fig)
    stacked = plot_cost_breakdown(frame, "Category", ["cost", "other"])
    require_equal(sum(_rectangle_heights(stacked.axes[0].patches)), 14.0)
    plt.close(stacked)
    interactive = plot_interactive_category_costs(frame, "Category", "cost")
    if not (list(interactive.data[0].y) == [5.0, 3.0]):
        raise AssertionError
    distribution = plot_interactive_cost_distribution(frame, "cost")
    require_equal(distribution.data[0].nbinsx, 50)
    require_equal(list(distribution.data[0].x), [3.0, 1.0, 4.0])
    corr = plot_cost_correlation_matrix(frame, ["cost", "other"])
    pixels = corr.axes[0].images[0].get_array()
    if pixels is None or pixels[0, 0] != pytest.approx(1.0):
        pytest.fail("Expected a correlation of 1 for a variable with itself")
    plt.close(corr)
    boxplot = plot_cost_boxplot(frame, "Category", "cost")
    if [label.get_text() for label in boxplot.axes[0].get_xticklabels()] != ["B", "A"]:
        raise AssertionError
    plt.close(boxplot)


def _rectangle_heights(patches: Iterable[Patch]) -> list[float]:
    heights: list[float] = []
    for artist in patches:
        if not isinstance(artist, Rectangle):
            pytest.fail("Expected a bar represented by a rectangle")
        heights.append(artist.get_height())
    return heights


def test_native_web_exports(tmp_path: Path) -> None:
    """Local API export preserves identifiers in CSV, XLSX, JSON and Parquet."""
    frame = pl.DataFrame({"id": ["001", "002", None], "cost": [1.0, 2.0, None]})
    frame.write_parquet(tmp_path / "source.parquet")
    with patch(
        "genomics_microcosting.monitoring.setup_standard_monitoring",
        return_value=(None,) * 5,
    ):
        app = create_app(tmp_path)
    client = app.test_client()
    for extension in ["csv", "excel", "json", "parquet"]:
        response = client.get(f"/api/export/source/{extension}")
        require_equal(response.status_code, HTTPStatus.OK)
        if extension == "parquet":
            assert_frame_equal(pl.read_parquet(io.BytesIO(response.data)), frame)
        elif extension == "excel":
            book = openpyxl.load_workbook(io.BytesIO(response.data), data_only=True)
            sheet = book.active
            if not isinstance(sheet, Worksheet):
                pytest.fail("Expected an active worksheet in the Excel export")
            require_equal(
                list(sheet.values),
                [
                    ("id", "cost"),
                    ("001", 1),
                    ("002", 2),
                    (None, None),
                ],
            )
            book.close()
        elif extension == "json":
            body = response.json
            if body is None or body[0]["id"] != "001":
                raise AssertionError
        elif "001" not in response.text:
            raise AssertionError
