# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Web-based visualization utilities for the microcosting analysis web interface."""

import base64
import io
from typing import Protocol, TypedDict, Unpack, cast
lazy from collections.abc import Callable

import matplotlib.pyplot as plt
import polars as pl
lazy from matplotlib.figure import Figure

from .visualization import plot_category_costs, plot_cost_distribution, plot_top_costs


class _PngOptions(TypedDict):
    format: str
    bbox_inches: str
    dpi: int


class _PngWriter(Protocol):
    def savefig(self, target: io.BytesIO, **options: Unpack[_PngOptions]) -> None: ...


def create_plot_base64[**P](
    plot_function: Callable[P, Figure],
    *args: P.args,
    **kwargs: P.kwargs,
) -> str:
    """Create a plot and return it as a base64 encoded string.

    Args:
        plot_function: Function that creates a matplotlib plot
        *args: Arguments to pass to the plot function
        **kwargs: Keyword arguments to pass to the plot function

    Returns:
        str: Base64 encoded PNG image

    """
    # Create the plot
    fig = plot_function(*args, **kwargs)

    # Save to a bytes buffer
    buf = io.BytesIO()
    cast("_PngWriter", fig).savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)

    # Convert to base64
    img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Close the figure to free memory
    plt.close(fig)

    return img_base64


def generate_visualization(
    data: pl.DataFrame,
    viz_type: str,
    column_name: str | None = None,
    category_column: str | None = None,
) -> str:
    """Generate a visualization based on the specified type.

    Args:
        data (pl.DataFrame): DataFrame containing the data
        viz_type (str): Type of visualization ("distribution", "category", "top")
        column_name (str, optional): Column to visualize
        category_column (str, optional): Category column for grouped visualizations

    Returns:
        str: Base64 encoded PNG image

    """
    # Find appropriate columns if not specified
    if column_name is None:
        # Find numeric columns
        numeric_columns = [
            name for name, dtype in data.schema.items() if dtype.is_numeric()
        ]
        if not numeric_columns:
            message = "No numeric columns found in data"
            raise ValueError(message)
        column_name = numeric_columns[0]

    if viz_type == "distribution":
        return create_plot_base64(plot_cost_distribution, data, column_name)
    if viz_type == "category":
        if category_column is None:
            # Find category columns
            category_columns = [
                col
                for col in data.columns
                if "Category" in col or "category" in col.lower()
            ]
            if not category_columns:
                message = "No category columns found in data"
                raise ValueError(message)
            category_column = category_columns[0]
        return create_plot_base64(
            plot_category_costs,
            data,
            category_column,
            column_name,
        )
    if viz_type == "top":
        return create_plot_base64(plot_top_costs, data, column_name)
    message = f"Unknown visualization type: {viz_type}"
    raise ValueError(message)


def get_available_columns(data: pl.DataFrame) -> dict[str, list[str]]:
    """Get lists of available columns for visualization.

    Args:
        data (pl.DataFrame): DataFrame containing the data

    Returns:
        dict: Dictionary with lists of numeric and category columns

    """
    numeric_columns = [
        name for name, dtype in data.schema.items() if dtype.is_numeric()
    ]
    category_columns = [
        col for col in data.columns if "Category" in col or "category" in col.lower()
    ]

    # If no explicit category columns found, look for likely candidates
    if not category_columns:
        category_columns = [
            col
            for col in data.columns
            if data[col].dtype == pl.String
            and data[col].drop_nulls().n_unique() < len(data) * 0.5
        ]  # Less than 50% unique values

    return {
        "numeric": numeric_columns[:20],  # Limit to first 20
        "category": category_columns[:10],  # Limit to first 10
    }
