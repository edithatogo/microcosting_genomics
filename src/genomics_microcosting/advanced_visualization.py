# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Advanced visualization tools for microcosting analysis with interactive features."""

import logging
from importlib import import_module
from pathlib import Path
from typing import Protocol, TypedDict, Unpack, cast
lazy from collections.abc import Sequence

import numpy as np
import polars as pl
lazy from matplotlib.container import BarContainer
lazy from matplotlib.figure import Figure
lazy from matplotlib.image import AxesImage
lazy from matplotlib.patches import Patch
lazy from numpy.typing import NDArray

from .visualization import load_prepared_data

try:
    import matplotlib as mpl

    mpl.use("Agg")
    import matplotlib.pyplot as plt
except ImportError, AttributeError:
    plt = None

HAS_MATPLOTLIB = plt is not None

logger = logging.getLogger(__name__)
_MINIMUM_SCATTER_COLUMNS = 2


class _PlotlyTrace(Protocol):
    @property
    def y(self) -> Sequence[float]: ...

    @property
    def x(self) -> Sequence[float]: ...


class _HistogramTrace(_PlotlyTrace, Protocol):
    @property
    def nbinsx(self) -> int | None: ...


class _Layout(TypedDict, total=False):
    xaxis_title: str
    yaxis_title: str
    showlegend: bool
    xaxis_tickangle: int
    title_text: str
    height: int


class PlotlyFigure[Trace: _PlotlyTrace = _PlotlyTrace](Protocol):
    """Plotly figure operations used by the interactive charts."""

    @property
    def data(self) -> tuple[Trace, ...]:
        """Return the figure's traces."""
        ...

    def update_layout(self, **layout: Unpack[_Layout]) -> PlotlyFigure[Trace]:
        """Apply layout settings."""
        ...

    def add_trace(self, trace: _PlotlyTrace, *, row: int, col: int) -> PlotlyFigure:
        """Add a trace to a subplot."""
        ...

    def show(self) -> None:
        """Display the interactive figure."""
        ...


class _HistogramOptions(TypedDict):
    x: str
    nbins: int
    title: str
    labels: dict[str, str]
    color_discrete_sequence: list[str]


class _PlotlyExpress(Protocol):
    def histogram(
        self,
        data_frame: pl.DataFrame,
        **options: Unpack[_HistogramOptions],
    ) -> PlotlyFigure[_HistogramTrace]: ...
    def bar(
        self,
        data_frame: pl.DataFrame,
        *,
        x: str,
        y: str,
        title: str,
        color_discrete_sequence: list[str],
    ) -> PlotlyFigure: ...
    def scatter(
        self,
        data_frame: pl.DataFrame,
        *,
        x: str,
        y: str,
        title: str,
        color: str | None = None,
    ) -> PlotlyFigure: ...


class _HistogramFactory(Protocol):
    def __call__(self, *, x: pl.Series, name: str) -> _PlotlyTrace: ...


class _BarFactory(Protocol):
    def __call__(
        self,
        *,
        x: Sequence[int] | pl.Series,
        y: pl.Series,
        name: str,
    ) -> _PlotlyTrace: ...


class _ScatterFactory(Protocol):
    def __call__(
        self,
        *,
        x: pl.Series,
        y: pl.Series,
        mode: str,
        name: str,
    ) -> _PlotlyTrace: ...


class _PlotlySubplots(Protocol):
    def __call__(
        self,
        *,
        rows: int,
        cols: int,
        subplot_titles: tuple[str, ...],
        specs: list[list[dict[str, bool]]],
    ) -> PlotlyFigure: ...


class _PlotlyOffline(Protocol):
    def plot(self, figure: PlotlyFigure, *, filename: str, auto_open: bool) -> str: ...


_express = cast("_PlotlyExpress", import_module("plotly.express"))
_graph_objects = import_module("plotly.graph_objects")
_histogram_trace = cast("_HistogramFactory", _graph_objects.Histogram)
_bar_trace = cast("_BarFactory", _graph_objects.Bar)
_scatter_trace = cast("_ScatterFactory", _graph_objects.Scatter)
_make_subplots = cast("_PlotlySubplots", import_module("plotly.subplots").make_subplots)
_offline = cast("_PlotlyOffline", import_module("plotly.offline"))


class _TextStyle(TypedDict, total=False):
    ha: str
    va: str
    fontsize: int
    rotation: float


class _ColoredBoxplot(TypedDict):
    boxes: list[Patch]


class _BarStyle(TypedDict):
    yerr: NDArray[np.float64]
    capsize: int
    alpha: float
    color: str
    edgecolor: str


class _Axes(Protocol):
    def bar(
        self,
        x: Sequence[int],
        height: pl.Series,
        **style: Unpack[_BarStyle],
    ) -> BarContainer: ...
    def boxplot(
        self,
        data: Sequence[NDArray[np.float64]],
        *,
        tick_labels: Sequence[str],
        patch_artist: bool,
    ) -> _ColoredBoxplot: ...
    def imshow(
        self,
        values: NDArray[np.float64],
        *,
        cmap: str,
        vmin: float,
        vmax: float,
    ) -> AxesImage: ...
    def set_xlabel(self, label: str) -> object: ...
    def set_ylabel(self, label: str) -> object: ...
    def set_title(self, label: str) -> object: ...
    def set_xticks(
        self,
        ticks: Sequence[int],
        *,
        labels: Sequence[str] | None = None,
        **style: Unpack[_TextStyle],
    ) -> object: ...
    def set_yticks(self, ticks: Sequence[int], *, labels: Sequence[str]) -> object: ...
    def set_xticklabels(
        self,
        labels: Sequence[str],
        **style: Unpack[_TextStyle],
    ) -> object: ...
    def grid(self, *, visible: bool, alpha: float) -> None: ...
    def text(
        self,
        x: float,
        y: float,
        label: str,
        **style: Unpack[_TextStyle],
    ) -> object: ...


class _Plotter(Protocol):
    def subplots(self, *, figsize: tuple[float, float]) -> tuple[Figure, _Axes]: ...
    def close(self, figure: Figure) -> None: ...
    def tight_layout(self) -> None: ...
    def xticks(self, *, rotation: float, ha: str) -> object: ...


class _ReportFigure(Protocol):
    def colorbar(self, image: AxesImage, *, ax: _Axes) -> object: ...
    def savefig(self, target: Path, *, bbox_inches: str, dpi: int) -> None: ...


def _matplotlib() -> _Plotter:
    if plt is None:
        message = "Matplotlib is required for this chart"
        raise RuntimeError(message)
    return cast("_Plotter", plt)


def plot_interactive_cost_distribution(
    data: pl.DataFrame,
    column_name: str,
    title: str = "Cost Distribution",
) -> PlotlyFigure[_HistogramTrace]:
    """Create an interactive histogram of cost distribution.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        column_name (str): Name of the column to plot.
        title (str): Title for the plot.

    Returns:
        plotly.graph_objects.Figure: The generated interactive figure.

    """
    if column_name not in data.columns:
        message = f"Column '{column_name}' not found in data"
        raise ValueError(message)

    # Remove NaN values
    values = data.select(column_name).drop_nulls()

    # Create interactive histogram
    fig = _express.histogram(
        values,
        x=column_name,
        nbins=50,
        title=title,
        labels={"y": "Frequency"},
        color_discrete_sequence=["skyblue"],
    )

    fig.update_layout(
        xaxis_title=column_name,
        yaxis_title="Frequency",
        showlegend=False,
    )

    return fig


def plot_interactive_category_costs(
    data: pl.DataFrame,
    category_column: str,
    cost_column: str,
    title: str = "Costs by Category",
) -> PlotlyFigure:
    """Create an interactive bar chart of costs by category.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_column (str): Name of the cost column to sum.
        title (str): Title for the plot.

    Returns:
        plotly.graph_objects.Figure: The generated interactive figure.

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

    # Create interactive bar chart
    fig = _express.bar(
        category_costs,
        x=category_column,
        y=cost_column,
        title=title,
        color_discrete_sequence=["lightcoral"],
    )

    fig.update_layout(
        xaxis_title=category_column,
        yaxis_title=f"Total {cost_column}",
        xaxis_tickangle=-45,
    )

    return fig


def plot_cost_trend_analysis(
    data: pl.DataFrame,
    category_column: str,
    cost_column: str,
    title: str = "Cost Trend Analysis",
) -> Figure:
    """Create a trend analysis plot showing cost distribution across categories.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_column (str): Name of the cost column to analyze.
        title (str): Title for the plot.

    Returns:
        matplotlib.figure.Figure: The generated figure.

    """
    if category_column not in data.columns:
        message = f"Column '{category_column}' not found in data"
        raise ValueError(message)
    if cost_column not in data.columns:
        message = f"Column '{cost_column}' not found in data"
        raise ValueError(message)

    # Group by category and calculate statistics
    grouped = (
        data.filter(pl.col(category_column).is_not_null())
        .group_by(category_column)
        .agg(
            [
                getattr(pl.col(cost_column).fill_nan(None), method)().alias(method)
                for method in ["count", "mean", "std", "min", "max"]
            ],
        )
        .sort(category_column)
    )

    plotter = _matplotlib()
    fig, ax = plotter.subplots(figsize=(12, 8))

    # Singleton groups have no sample standard deviation.
    deviations = grouped["std"].fill_null(0.0).cast(pl.Float64).to_numpy()
    maximum = cast("float | None", grouped["max"].cast(pl.Float64).max())
    label_offset = (maximum or 0.0) * 0.01

    # Create bar plot with error bars
    bars = ax.bar(
        range(len(grouped)),
        grouped["mean"],
        yerr=deviations,
        capsize=5,
        alpha=0.7,
        color="lightgreen",
        edgecolor="black",
    )

    ax.set_xlabel(category_column)
    ax.set_ylabel(f"Average {cost_column}")
    ax.set_title(title)
    ax.set_xticks(range(len(grouped)))
    ax.set_xticklabels(
        [str(category) for category in grouped[category_column]],
        rotation=45,
        ha="right",
    )
    ax.grid(visible=True, alpha=0.3)

    # Add count labels
    for bar, count, deviation in zip(
        bars.patches,
        grouped["count"],
        deviations,
        strict=True,
    ):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + deviation + label_offset,
            f"n={count}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    plotter.tight_layout()
    return fig


def plot_cost_correlation_matrix(
    data: pl.DataFrame,
    cost_columns: list[str],
    title: str = "Cost Correlation Matrix",
) -> Figure:
    """Create a correlation matrix heatmap for cost columns.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        cost_columns (list): List of cost column names to include.
        title (str): Title for the plot.

    Returns:
        matplotlib.figure.Figure: The generated figure.

    """
    for col in cost_columns:
        if col not in data.columns:
            message = f"Column '{col}' not found in data"
            raise ValueError(message)

    # Calculate correlation matrix
    corr_matrix = np.array(
        [
            [data.select(pl.corr(a, b)).item() for b in cost_columns]
            for a in cost_columns
        ],
        dtype=float,
    )

    plotter = _matplotlib()
    fig, ax = plotter.subplots(figsize=(10, 8))

    # Create heatmap
    image = ax.imshow(corr_matrix, cmap="coolwarm", vmin=-1, vmax=1)
    cast("_ReportFigure", fig).colorbar(image, ax=ax)
    ax.set_xticks(
        range(len(cost_columns)),
        labels=cost_columns,
        rotation=45,
        ha="right",
    )
    ax.set_yticks(range(len(cost_columns)), labels=cost_columns)
    for i in range(len(cost_columns)):
        for j in range(len(cost_columns)):
            ax.text(j, i, f"{corr_matrix[i, j]:.2f}", ha="center", va="center")

    ax.set_title(title)
    plotter.tight_layout()
    return fig


def plot_interactive_cost_scatter(
    data: pl.DataFrame,
    x_column: str,
    y_column: str,
    category_column: str | None = None,
    title: str = "Cost Scatter Plot",
) -> PlotlyFigure:
    """Create an interactive scatter plot of costs.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        x_column (str): Name of the column for x-axis.
        y_column (str): Name of the column for y-axis.
        category_column (str, optional): Name of the column for coloring points.
        title (str): Title for the plot.

    Returns:
        plotly.graph_objects.Figure: The generated interactive figure.

    """
    if x_column not in data.columns:
        message = f"Column '{x_column}' not found in data"
        raise ValueError(message)
    if y_column not in data.columns:
        message = f"Column '{y_column}' not found in data"
        raise ValueError(message)

    # Remove rows with NaN values in either column
    clean_data = data.select(
        [x_column, y_column]
        + (
            [category_column]
            if category_column and category_column not in [x_column, y_column]
            else []
        ),
    ).drop_nulls([x_column, y_column])

    if category_column and category_column in data.columns:
        fig = _express.scatter(
            clean_data,
            x=x_column,
            y=y_column,
            color=category_column,
            title=title,
        )
    else:
        fig = _express.scatter(
            clean_data,
            x=x_column,
            y=y_column,
            title=title,
        )

    fig.update_layout(
        xaxis_title=x_column,
        yaxis_title=y_column,
    )

    return fig


def plot_cost_boxplot(
    data: pl.DataFrame,
    category_column: str,
    cost_column: str,
    title: str = "Cost Distribution by Category",
) -> Figure:
    """Create a boxplot showing cost distribution across categories.

    Args:
        data (pl.DataFrame): DataFrame containing the data.
        category_column (str): Name of the category column.
        cost_column (str): Name of the cost column to analyze.
        title (str): Title for the plot.

    Returns:
        matplotlib.figure.Figure: The generated figure.

    """
    if category_column not in data.columns:
        message = f"Column '{category_column}' not found in data"
        raise ValueError(message)
    if cost_column not in data.columns:
        message = f"Column '{cost_column}' not found in data"
        raise ValueError(message)

    # Remove rows with NaN values
    clean_data = data[[category_column, cost_column]].drop_nulls()

    if clean_data.is_empty():
        message = "No valid data to plot"
        raise ValueError(message)

    groups = clean_data.partition_by(category_column, maintain_order=True)
    boxplot_data = [group[cost_column].cast(pl.Float64).to_numpy() for group in groups]
    boxplot_labels = [str(group[category_column][0]) for group in groups]

    plotter = _matplotlib()
    fig, ax = plotter.subplots(figsize=(12, 8))

    # Create boxplot
    bp = ax.boxplot(boxplot_data, tick_labels=boxplot_labels, patch_artist=True)

    # Color the boxes
    colors = ["lightblue", "lightgreen", "lightcoral", "lightyellow", "lightpink"]
    for patch, color in zip(
        bp["boxes"],
        colors * (len(bp["boxes"]) // len(colors) + 1),
        strict=False,
    ):
        patch.set_facecolor(color)

    ax.set_xlabel(category_column)
    ax.set_ylabel(cost_column)
    ax.set_title(title)
    ax.grid(visible=True, alpha=0.3)
    plotter.xticks(rotation=45, ha="right")
    plotter.tight_layout()
    return fig


def create_interactive_dashboard(data_dict: dict[str, pl.DataFrame]) -> PlotlyFigure:
    """Create an interactive dashboard with multiple visualizations.

    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys.

    Returns:
        plotly.graph_objects.Figure: The generated interactive dashboard.

    """
    if "detailed_table" not in data_dict:
        message = "Detailed table not found in prepared data"
        raise ValueError(message)

    detailed_data = data_dict["detailed_table"]

    # Find cost columns
    cost_columns = [
        col for col in detailed_data.columns if "unit_cost" in col or "price" in col
    ]
    category_columns = [col for col in detailed_data.columns if "Category" in col]

    if not cost_columns or not category_columns:
        # Try to find any numeric and categorical columns
        numeric_columns = [n for n, d in detailed_data.schema.items() if d.is_numeric()]
        categorical_columns = [
            n for n, d in detailed_data.schema.items() if d == pl.String
        ]

        if not cost_columns and numeric_columns:
            cost_columns = [numeric_columns[0]]
        if not category_columns and categorical_columns:
            category_columns = [categorical_columns[0]]

    # Create subplots
    fig = _make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Cost Distribution",
            "Costs by Category",
            "Top Costs",
            "Cost Scatter Plot",
        ),
        specs=[
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}],
        ],
    )

    # Add plots if we have the required data
    if cost_columns:
        # Cost distribution (simplified for subplot)
        values = detailed_data[cost_columns[0]].drop_nulls()
        histogram_name = f"Distribution of {cost_columns[0]}"
        fig.add_trace(
            _histogram_trace(x=values[:1000], name=histogram_name),
            row=1,
            col=1,
        )

        # Top costs
        top_costs = detailed_data.sort(
            cost_columns[0],
            descending=True,
            nulls_last=True,
            maintain_order=True,
        ).head(20)
        fig.add_trace(
            _bar_trace(
                x=list(range(len(top_costs))),
                y=top_costs[cost_columns[0]],
                name=f"Top 20 {cost_columns[0]}",
            ),
            row=2,
            col=1,
        )

    if category_columns and cost_columns:
        # Costs by category
        category_costs = (
            detailed_data.filter(pl.col(category_columns[0]).is_not_null())
            .group_by(category_columns[0])
            .agg(pl.col(cost_columns[0]).fill_nan(None).sum())
            .sort(cost_columns[0], descending=True)
        )
        fig.add_trace(
            _bar_trace(
                x=category_costs[category_columns[0]][:15],
                y=category_costs[cost_columns[0]][:15],
                name=f"Total {cost_columns[0]} by {category_columns[0]}",
            ),
            row=1,
            col=2,
        )

        # Scatter plot (if we have two numeric columns)
        if len(cost_columns) >= _MINIMUM_SCATTER_COLUMNS:
            clean_data = detailed_data[[cost_columns[0], cost_columns[1]]].drop_nulls()
            fig.add_trace(
                _scatter_trace(
                    x=clean_data[cost_columns[0]][:500],
                    y=clean_data[cost_columns[1]][:500],
                    mode="markers",
                    name=f"{cost_columns[0]} vs {cost_columns[1]}",
                ),
                row=2,
                col=2,
            )

    fig.update_layout(
        title_text="Interactive Microcosting Analysis Dashboard",
        showlegend=False,
        height=800,
    )

    return fig


def save_interactive_plot(fig: PlotlyFigure, output_file: str | Path) -> None:
    """Save an interactive plot as HTML.

    Args:
        fig (plotly.graph_objects.Figure): The figure to save.
        output_file (str or Path): Path to output HTML file.

    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    _offline.plot(fig, filename=str(output_file), auto_open=False)


def _save_static_plot(figure: Figure, target: Path) -> str:
    try:
        cast("_ReportFigure", figure).savefig(target, bbox_inches="tight", dpi=300)
    finally:
        _matplotlib().close(figure)
    return target.name


def _write_static_charts(
    data: pl.DataFrame,
    cost_columns: list[str],
    category: str | None,
    output_dir: Path,
    figures: list[str],
) -> None:
    if category is not None and cost_columns:
        cost = cost_columns[0]
        trend = plot_cost_trend_analysis(
            data,
            category,
            cost,
            f"Cost Trend Analysis: {cost} by {category}",
        )
        target = output_dir / f"cost_trend_analysis_{category}.png"
        figures.append(_save_static_plot(trend, target))

    if len(cost_columns) >= _MINIMUM_SCATTER_COLUMNS:
        correlation = plot_cost_correlation_matrix(
            data,
            cost_columns[:5],
            "Cost Correlation Matrix (Top 5 Cost Columns)",
        )
        figures.append(
            _save_static_plot(correlation, output_dir / "cost_correlation_matrix.png"),
        )

    if category is not None and cost_columns:
        try:
            boxplot = plot_cost_boxplot(
                data,
                category,
                cost_columns[0],
                f"Cost Distribution by {category}",
            )
            figures.append(
                _save_static_plot(boxplot, output_dir / f"cost_boxplot_{category}.png"),
            )
        except OSError, RuntimeError, ValueError, TypeError, pl.exceptions.PolarsError:
            logger.warning("Could not create boxplot", exc_info=True)


def _filename_label(column: str) -> str:
    label = "".join(
        character
        for character in column
        if character.isalnum() or character in (" ", "-", "_")
    )
    return label.rstrip().replace(" ", "_")


def _write_interactive_charts(
    data: pl.DataFrame,
    cost_columns: list[str],
    category: str | None,
    output_dir: Path,
    figures: list[str],
) -> None:
    if not cost_columns:
        return
    cost = cost_columns[0]
    cost_label = _filename_label(cost)
    distribution = plot_interactive_cost_distribution(
        data,
        cost,
        f"Interactive Distribution of {cost}",
    )
    target = output_dir / f"interactive_cost_distribution_{cost_label}.html"
    save_interactive_plot(distribution, target)
    figures.append(target.name)

    if category is None:
        return
    category_costs = plot_interactive_category_costs(
        data,
        category,
        cost,
        f"Interactive Costs by {category}",
    )
    category_label = _filename_label(category)
    target = output_dir / f"interactive_category_costs_{category_label}.html"
    save_interactive_plot(category_costs, target)
    figures.append(target.name)

    if len(cost_columns) >= _MINIMUM_SCATTER_COLUMNS:
        other_cost = cost_columns[1]
        scatter = plot_interactive_cost_scatter(
            data,
            cost,
            other_cost,
            category,
            f"Interactive Scatter: {cost} vs {other_cost}",
        )
        scatter_label = f"{cost_label}_vs_{_filename_label(other_cost)}"
        target = output_dir / f"interactive_cost_scatter_{scatter_label}.html"
        save_interactive_plot(scatter, target)
        figures.append(target.name)


def create_comprehensive_visualization_report(
    data_dict: dict[str, pl.DataFrame],
    output_dir: str | Path,
) -> list[str]:
    """Create a comprehensive visualization report with multiple chart types.

    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys.
        output_dir (str or Path): Directory to save plots.

    Returns:
        list: List of generated figure filenames.

    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    figures: list[str] = []

    if "detailed_table" not in data_dict:
        logger.info(
            "%s",
            "Warning: detailed_table not found in data. Skipping detailed plots.",
        )
        return figures

    detailed_data = data_dict["detailed_table"]

    # Find cost columns
    cost_columns = [
        col for col in detailed_data.columns if "unit_cost" in col or "price" in col
    ]
    category_columns = [col for col in detailed_data.columns if "Category" in col]

    if not cost_columns:
        # Try to find any numeric columns
        numeric_columns = [n for n, d in detailed_data.schema.items() if d.is_numeric()]
        if numeric_columns:
            cost_columns = [numeric_columns[0]]

    category = category_columns[0] if category_columns else None
    try:
        _write_static_charts(detailed_data, cost_columns, category, output_dir, figures)
        _write_interactive_charts(
            detailed_data,
            cost_columns,
            category,
            output_dir,
            figures,
        )
        dashboard = create_interactive_dashboard(data_dict)
        target = output_dir / "interactive_dashboard.html"
        save_interactive_plot(dashboard, target)
        figures.append(target.name)
    except Exception:
        logger.exception("Error creating enhanced visualizations")

    return figures


# Example usage function
def example_usage() -> None:
    """Demonstrate the advanced visualization functions."""
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

        # Create an interactive plot if we have data
        if cost_columns:
            try:
                fig = plot_interactive_cost_distribution(detailed_data, cost_columns[0])
                fig.show()
            except OSError, ValueError, RuntimeError:
                logger.exception("Could not create interactive plot")
    else:
        logger.info("%s", "Detailed table not found in prepared data")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
