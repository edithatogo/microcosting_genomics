# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Visualization tools for microcosting analysis."""

import logging
from pathlib import Path
from typing import Protocol, TypedDict, Unpack, cast
lazy from collections.abc import Callable, Sequence

import numpy as np
import polars as pl
lazy from matplotlib.container import BarContainer
lazy from matplotlib.figure import Figure
lazy from matplotlib.text import Text
lazy from numpy.typing import NDArray

try:
    import matplotlib as mpl

    mpl.use("Agg")
    import matplotlib.pyplot as plt
except ImportError, AttributeError:
    plt = None

HAS_MATPLOTLIB = plt is not None
logger = logging.getLogger(__name__)


class _HistogramStyle(TypedDict):
    bins: int
    alpha: float
    color: str
    edgecolor: str


class _BarStyle(TypedDict, total=False):
    bottom: NDArray[np.float64]
    color: str
    label: str


class _TextStyle(TypedDict, total=False):
    ha: str
    va: str
    fontsize: int
    rotation: float


class _CostAxes(Protocol):
    def hist(
        self,
        x: NDArray[np.float64],
        **style: Unpack[_HistogramStyle],
    ) -> object: ...
    def bar(
        self,
        x: Sequence[int] | Sequence[str],
        height: NDArray[np.float64],
        **style: Unpack[_BarStyle],
    ) -> BarContainer: ...
    def set_xlabel(self, label: str) -> object: ...
    def set_ylabel(self, label: str) -> object: ...
    def set_title(self, label: str) -> object: ...
    def set_xticks(self, ticks: Sequence[int]) -> object: ...
    def set_xticklabels(
        self,
        labels: Sequence[str],
        **style: Unpack[_TextStyle],
    ) -> object: ...
    def get_xticklabels(self) -> list[Text]: ...
    def grid(self, *, visible: bool, alpha: float) -> None: ...
    def legend(self, *, title: str) -> object: ...
    def text(
        self,
        x: float,
        y: float,
        s: str,
        **style: Unpack[_TextStyle],
    ) -> object: ...


class _ChartPlotter(Protocol):
    def subplots(self, *, figsize: tuple[float, float]) -> tuple[Figure, _CostAxes]: ...
    def close(self, figure: Figure) -> None: ...
    def show(self) -> None: ...


class _ImageWriter(Protocol):
    def savefig(self, target: Path, *, bbox_inches: str, dpi: int) -> None: ...


def _plotter() -> _ChartPlotter:
    if plt is None:
        message = "Matplotlib is required for this chart"
        raise RuntimeError(message)
    return cast("_ChartPlotter", plt)


def load_prepared_data(data_dir: str | Path | None = None) -> dict[str, pl.DataFrame]:
    """Load prepared data from the data directory.

    Args:
        data_dir (str or Path, optional): Path to the data directory.
            If None, uses the default data/prepared directory.

    Returns:
        dict: Dictionary of loaded DataFrames with keys as table names.

    """
    if data_dir is None:
        data_dir = Path(__file__).resolve().parents[2] / "data" / "prepared"
    else:
        data_dir = Path(data_dir)

    if not data_dir.exists():
        message = f"Data directory not found: {data_dir}"
        raise FileNotFoundError(message)

    data_files = list(data_dir.glob("*.parquet"))
    data: dict[str, pl.DataFrame] = {}

    for file_path in data_files:
        table_name = file_path.stem
        try:
            data[table_name] = pl.read_parquet(file_path)
        except OSError, pl.exceptions.PolarsError:
            logger.exception("Could not load %s", file_path)

    return data


def plot_cost_distribution(
    data: pl.DataFrame,
    column_name: str,
    title: str = "Cost Distribution",
    figsize: tuple[float, float] = (10, 6),
) -> Figure:
    """Plot the distribution of costs from a specified column.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        column_name (str): Name of the column to plot.
        title (str): Title for the plot.
        figsize (tuple): Figure size (width, height).

    Returns:
        matplotlib.figure.Figure: The generated figure.

    """
    if column_name not in data.columns:
        message = f"Column '{column_name}' not found in data"
        raise ValueError(message)

    fig, ax = _plotter().subplots(figsize=figsize)

    # Remove NaN values
    values = data[column_name].cast(pl.Float64).fill_nan(None).drop_nulls().to_numpy()

    # Plot histogram
    ax.hist(values, bins=50, alpha=0.7, color="skyblue", edgecolor="black")
    ax.set_xlabel(column_name)
    ax.set_ylabel("Frequency")
    ax.set_title(title)
    ax.grid(visible=True, alpha=0.3)

    return fig


def plot_category_costs(
    data: pl.DataFrame,
    category_column: str,
    cost_column: str,
    title: str = "Costs by Category",
    figsize: tuple[float, float] = (12, 8),
) -> Figure:
    """Plot total costs by category.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_column (str): Name of the cost column to sum.
        title (str): Title for the plot.
        figsize (tuple): Figure size (width, height).

    Returns:
        matplotlib.figure.Figure: The generated figure.

    """
    if category_column not in data.columns:
        message = f"Column '{category_column}' not found in data"
        raise ValueError(message)
    if cost_column not in data.columns:
        message = f"Column '{cost_column}' not found in data"
        raise ValueError(message)

    # Group by category and sum costs
    category_costs = (
        data.filter(pl.col(category_column).is_not_null())
        .group_by(category_column)
        .agg(pl.col(cost_column).fill_nan(None).sum())
        .sort([cost_column, category_column], descending=[True, False])
    )

    fig, ax = _plotter().subplots(figsize=figsize)

    # Create bar plot
    values = category_costs[cost_column].cast(pl.Float64).to_numpy()
    bars = ax.bar(
        range(len(category_costs)),
        values,
        color="lightcoral",
    )
    ax.set_xlabel(category_column)
    ax.set_ylabel(f"Total {cost_column}")
    ax.set_title(title)
    ax.set_xticks(range(len(category_costs)))
    ax.set_xticklabels(
        [str(label) for label in category_costs[category_column]],
        rotation=45,
        ha="right",
    )
    ax.grid(visible=True, alpha=0.3)

    # Add value labels on bars
    for bar, value in zip(bars.patches, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + value * 0.01,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()
    return fig


def plot_cost_breakdown(
    data: pl.DataFrame,
    category_column: str,
    cost_columns: list[str],
    title: str = "Cost Breakdown by Category",
    figsize: tuple[float, float] = (12, 8),
) -> Figure:
    """Plot cost breakdown by category for multiple cost columns.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_columns (list): List of cost column names to include.
        title (str): Title for the plot.
        figsize (tuple): Figure size (width, height).

    Returns:
        matplotlib.figure.Figure: The generated figure.

    """
    if category_column not in data.columns:
        message = f"Column '{category_column}' not found in data"
        raise ValueError(message)

    for col in cost_columns:
        if col not in data.columns:
            message = f"Column '{col}' not found in data"
            raise ValueError(message)

    # Group by category and sum costs for each column
    grouped_data = (
        data.filter(pl.col(category_column).is_not_null())
        .group_by(category_column)
        .agg(pl.col(cost_columns).fill_nan(None).sum())
        .sort(category_column)
    )

    fig, ax = _plotter().subplots(figsize=figsize)

    # Create stacked bar plot
    bottom = np.zeros(grouped_data.height)
    for column in cost_columns:
        values = grouped_data[column].cast(pl.Float64).to_numpy()
        ax.bar(
            [str(label) for label in grouped_data[category_column]],
            values,
            bottom=bottom,
            label=column,
        )
        bottom = bottom + values
    ax.set_xlabel(category_column)
    ax.set_ylabel("Total Cost")
    ax.set_title(title)
    ax.legend(title="Cost Components")
    ax.grid(visible=True, alpha=0.3)
    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_horizontalalignment("right")
    fig.tight_layout()

    return fig


def plot_top_costs(
    data: pl.DataFrame,
    cost_column: str,
    top_n: int = 10,
    title: str = "Top Costs",
    figsize: tuple[float, float] = (10, 6),
) -> Figure:
    """Plot the top N costs.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        cost_column (str): Name of the cost column.
        top_n (int): Number of top costs to display.
        title (str): Title for the plot.
        figsize (tuple): Figure size (width, height).

    Returns:
        matplotlib.figure.Figure: The generated figure.

    """
    if cost_column not in data.columns:
        message = f"Column '{cost_column}' not found in data"
        raise ValueError(message)

    # Sort by cost and take top N
    top_costs = (
        data.with_row_index("__source_row")
        .sort([cost_column, "__source_row"], descending=[True, False], nulls_last=True)
        .head(max(0, top_n))
    )

    # If there's a descriptive column, use it for labels
    label_column = None
    for col in ["Step", "Test", "Category", "Sub-Category"]:
        if col in data.columns:
            label_column = col
            break

    if label_column is None:
        labels = [f"Item {i + 1}" for i in range(len(top_costs))]
    else:
        labels = [str(label) for label in top_costs[label_column].fill_null("Unknown")]

    fig, ax = _plotter().subplots(figsize=figsize)

    values = top_costs[cost_column].cast(pl.Float64).to_numpy()
    bars = ax.bar(range(len(top_costs)), values, color="gold")
    ax.set_xlabel("Items")
    ax.set_ylabel(cost_column)
    ax.set_title(title)
    ax.set_xticks(range(len(top_costs)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(visible=True, alpha=0.3)

    # Add value labels on bars
    for bar, value in zip(bars.patches, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + value * 0.01,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()
    return fig


def create_summary_dashboard(
    data_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> list[Figure]:
    """Create a summary dashboard with common visualizations.

    Args:
        data_dir (str or Path, optional): Path to the data directory.
        output_dir (str or Path, optional): Path to save plots. If None, shows plots.

    Returns:
        list: List of generated figure objects.

    """
    # Load data
    data_dict = load_prepared_data(data_dir)

    if "detailed_table" not in data_dict:
        message = "Detailed table not found in prepared data"
        raise ValueError(message)

    detailed_data = data_dict["detailed_table"]

    # Find cost columns (those with 'unit_cost' or 'price' in the name)
    cost_columns = [
        col for col in detailed_data.columns if "unit_cost" in col or "price" in col
    ]
    if not cost_columns:
        # Try to find any numeric columns
        numeric_columns = [
            name for name, dtype in detailed_data.schema.items() if dtype.is_numeric()
        ]
        if numeric_columns:
            cost_columns = [numeric_columns[0]]  # Use the first numeric column

    figures: list[Figure] = []
    if cost_columns:
        cost = cost_columns[0]
        _add_dashboard_chart(
            figures,
            lambda: plot_cost_distribution(
                detailed_data,
                cost,
                f"Distribution of {cost}",
            ),
            output_dir,
            f"cost_distribution_{cost}.png",
        )
        category_columns = [col for col in detailed_data.columns if "Category" in col]
        if category_columns:
            category = category_columns[0]
            _add_dashboard_chart(
                figures,
                lambda: plot_category_costs(
                    detailed_data,
                    category,
                    cost,
                    f"Total {cost} by {category}",
                ),
                output_dir,
                f"costs_by_{category}.png",
            )
        _add_dashboard_chart(
            figures,
            lambda: plot_top_costs(
                detailed_data,
                cost,
                top_n=15,
                title=f"Top 15 {cost}",
            ),
            output_dir,
            f"top_{cost}.png",
        )

    if not output_dir:
        _plotter().show()

    return figures


def _add_dashboard_chart(
    figures: list[Figure],
    plot: Callable[[], Figure],
    output_dir: str | Path | None,
    filename: str,
) -> None:
    try:
        figure = plot()
        figures.append(figure)
        if output_dir:
            cast("_ImageWriter", figure).savefig(
                Path(output_dir) / filename,
                bbox_inches="tight",
                dpi=300,
            )
            _plotter().close(figure)
    except Exception:
        logger.exception("Could not create chart %s", filename)


# Example usage function
def example_usage() -> None:
    """Demonstrate the visualization functions."""
    logger.info("%s", "Loading data...")
    data_dict = load_prepared_data()

    if "detailed_table" in data_dict:
        detailed_data = data_dict["detailed_table"]
        logger.info("%s", f"Loaded detailed table with {len(detailed_data)} rows")

        # Find cost columns
        cost_columns = [
            col for col in detailed_data.columns if "unit_cost" in col or "price" in col
        ]
        category_columns = [col for col in detailed_data.columns if "Category" in col]

        logger.info("%s", f"Found cost columns: {cost_columns}")
        logger.info("%s", f"Found category columns: {category_columns}")

        # Create a simple plot if we have data
        if cost_columns:
            try:
                plot_cost_distribution(detailed_data, cost_columns[0])
                _plotter().show()
            except Exception:
                logger.exception("Could not create plot")
    else:
        logger.info("%s", "Detailed table not found in prepared data")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
