# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Probabilistic Sensitivity Analysis (PSA) module for microcosting analysis.

This module provides functionality to perform probabilistic sensitivity analysis
using Monte Carlo simulation to quantify uncertainty in cost outcomes.
"""

import logging
from pathlib import Path
from typing import Protocol, TypedDict, cast

import numpy as np
lazy import polars as pl
lazy from matplotlib.figure import Figure
lazy from numpy.typing import NDArray

from .sensitivity_evidence import archived_draws, markdown_table

try:
    import matplotlib as mpl

    mpl.use("Agg")
    import matplotlib.pyplot as plt
except ImportError, AttributeError:
    plt = None

from .data_manager import DataManager
from .logging_config import get_logger

logger = get_logger(__name__)
HAS_MATPLOTLIB = plt is not None


class _HistogramAxes(Protocol):
    def hist(
        self,
        x: NDArray[np.float64],
        *,
        bins: int,
        alpha: float,
        color: str,
        edgecolor: str,
    ) -> object: ...

    def set_xlabel(self, label: str) -> object: ...
    def set_ylabel(self, label: str) -> object: ...
    def set_title(self, label: str) -> object: ...
    def grid(self, *, visible: bool, alpha: float) -> None: ...
    def legend(self) -> object: ...

    def axvline(
        self,
        x: float,
        *,
        color: str,
        linestyle: str,
        label: str,
    ) -> object: ...


class _Pyplot(Protocol):
    def subplots(
        self,
        *,
        figsize: tuple[float, float],
    ) -> tuple[Figure, _HistogramAxes]: ...


class DistributionSpec(TypedDict, total=False):
    """Declared distribution and numerical parameters for one simulated input."""

    distribution: str
    parameters: dict[str, float]


class PSAAnalyzer:
    """Analyzer for performing Probabilistic Sensitivity Analysis."""

    def __init__(
        self,
        data_manager: DataManager,
        *,
        rng: np.random.Generator | None = None,
    ) -> None:
        """Initialize the PSAAnalyzer.

        Args:
            data_manager: DataManager instance for accessing prepared data
            rng: Optional generator for reproducible probability draws

        """
        self.data_manager = data_manager
        self.rng = rng if rng is not None else np.random.default_rng()
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    def load_psa_parameters(self) -> dict[str, pl.DataFrame]:
        """Load PSA parameters from prepared sheets.

        Returns:
            Dictionary of PSA parameter sheets

        """
        self.logger.info("Loading PSA parameters...")

        psa_sheets: dict[str, pl.DataFrame] = {}
        psa_sheet_names = [
            "PSA",
            "psa",
        ]

        for sheet_name in psa_sheet_names:
            try:
                df = self.data_manager.load_sheet(sheet_name)
                if df is not None:
                    psa_sheets[sheet_name] = df
                    self.logger.info("  Loaded %s with shape %s", sheet_name, df.shape)
                else:
                    self.logger.debug("  Could not load %s", sheet_name)
            except OSError, ValueError, pl.exceptions.PolarsError:
                self.logger.debug("  Error loading %s", sheet_name, exc_info=True)

        return psa_sheets

    def sample_from_distribution(
        self,
        distribution_type: str,
        parameters: dict[str, float],
    ) -> NDArray[np.float64]:
        """Sample values from a specified probability distribution.

        Args:
            distribution_type: Distribution type, such as normal, uniform or triangular.
            parameters: Dictionary of distribution parameters

        Returns:
            Array of sampled values

        """
        raw_size = parameters.get("size", 1000)
        if raw_size <= 0 or not float(raw_size).is_integer():
            message = "Sample size must be a positive integer"
            raise ValueError(message)
        size = int(raw_size)

        if distribution_type == "normal":
            mean = parameters.get("mean", 0)
            std = parameters.get("std", 1)
            return self.rng.normal(mean, std, size)
        if distribution_type == "uniform":
            low = parameters.get("low", 0)
            high = parameters.get("high", 1)
            return self.rng.uniform(low, high, size)
        if distribution_type == "triangular":
            left = parameters.get("left", 0)
            mode = parameters.get("mode", 0.5)
            right = parameters.get("right", 1)
            return self.rng.triangular(left, mode, right, size)
        # Default to normal distribution
        mean = parameters.get("mean", 0)
        std = parameters.get("std", 1)
        return self.rng.normal(mean, std, size)

    def perform_monte_carlo_simulation(
        self,
        parameters: dict[str, DistributionSpec],
        iterations: int = 1000,
    ) -> dict[str, NDArray[np.float64]]:
        """Perform Monte Carlo simulation with specified parameters.

        Args:
            parameters: Dictionary mapping parameter names to distribution info
            iterations: Number of Monte Carlo iterations

        Returns:
            Dictionary of simulation results

        """
        self.logger.info(
            "Performing Monte Carlo simulation with %s iterations...",
            iterations,
        )

        results: dict[str, NDArray[np.float64]] = {}

        # Sample from each parameter distribution
        for param_name, param_info in parameters.items():
            dist_type = param_info.get("distribution", "normal")
            dist_params = dict(param_info.get("parameters", {}))
            dist_params["size"] = iterations

            samples = self.sample_from_distribution(dist_type, dist_params)
            results[param_name] = samples

        return results

    def calculate_cost_outcomes(
        self,
        simulation_results: dict[str, NDArray[np.float64]],
    ) -> NDArray[np.float64]:
        """Calculate cost outcomes from simulation results.

        Args:
            simulation_results: Dictionary of parameter samples from simulation

        Returns:
            Array of cost outcomes

        """
        # This is a simplified implementation
        # In a real implementation, this would run the full cost model
        # with the sampled parameter values

        # For demonstration, we'll just combine some parameters
        # to create cost outcomes
        if (
            "labour_cost" in simulation_results
            and "equipment_cost" in simulation_results
        ):
            labour_costs = simulation_results["labour_cost"]
            equipment_costs = simulation_results["equipment_cost"]
            # Simple cost model: total cost = labour + equipment + some fixed costs
            fixed_costs = 500  # Placeholder fixed costs
            return labour_costs + equipment_costs + fixed_costs
        # If we don't have specific parameters, return a simple distribution
        return self.rng.normal(1000, 200, len(next(iter(simulation_results.values()))))

    def generate_psa_histogram(
        self,
        cost_outcomes: NDArray[np.float64],
        title: str = "PSA Cost Outcomes Distribution",
    ) -> Figure | None:
        """Generate a histogram of PSA cost outcomes.

        Args:
            cost_outcomes: Array of cost outcomes from simulation
            title: Title for the chart

        Returns:
            Matplotlib figure with histogram or None if matplotlib unavailable

        """
        if plt is None:
            logger.warning("Matplotlib not available, skipping chart generation")
            return None

        fig, ax = cast("_Pyplot", plt).subplots(figsize=(10, 6))
        ax.hist(cost_outcomes, bins=50, alpha=0.7, color="skyblue", edgecolor="black")
        ax.set_xlabel("Cost Outcome ($)")
        ax.set_ylabel("Frequency")
        ax.set_title(title)
        ax.grid(visible=True, alpha=0.3)

        # Add statistics lines
        mean_cost = np.mean(cost_outcomes)
        std_cost = np.std(cost_outcomes)

        ax.axvline(
            float(mean_cost),
            color="red",
            linestyle="--",
            label=f"Mean: ${mean_cost:.2f}",
        )
        ax.axvline(
            float(mean_cost - std_cost),
            color="orange",
            linestyle=":",
            label=f"Mean ± Std: ${mean_cost - std_cost:.2f}",
        )
        ax.axvline(
            float(mean_cost + std_cost),
            color="orange",
            linestyle=":",
            label=f"Mean + Std: ${mean_cost + std_cost:.2f}",
        )

        ax.legend()
        fig.tight_layout()
        return fig

    def calculate_confidence_intervals(
        self,
        cost_outcomes: NDArray[np.float64],
        percentiles: tuple[float, ...] = (2.5, 25, 50, 75, 97.5),
    ) -> dict[str, float]:
        """Calculate confidence intervals for cost outcomes.

        Args:
            cost_outcomes: Array of cost outcomes from simulation
            percentiles: List of percentiles to calculate

        Returns:
            Dictionary of percentile values

        """
        results: dict[str, float] = {}
        for percentile in percentiles:
            results[f"{percentile}%"] = float(np.percentile(cost_outcomes, percentile))
        return results

    def generate_psa_report(
        self,
        iterations: int = 1000,
        output_file: str | None = None,
    ) -> str:
        """Generate a comprehensive PSA analysis report.

        Args:
            iterations: Requested iterations, recorded for API compatibility
            output_file: Optional file path to save the report

        Returns:
            Report as a string

        """
        self.logger.debug(
            "Using all archived draws for the requested %s iterations",
            iterations,
        )
        paths = list(
            (self.data_manager.data_dir.parent / "notebooks").glob("PSA Update*.ipynb"),
        )
        if len(paths) != 1:
            message = "An identifiable archived PSA notebook is required"
            raise ValueError(message)
        table = archived_draws(paths[0])
        report = (
            "# Probabilistic sensitivity analysis\n\n"
            "Each assay has 10,000 archived draws. Lower and upper are the "
            "2.5th and 97.5th percentiles of the simulated costs. "
            "The report uses the full archived draw set for any "
            "requested iteration count.\n\n" + markdown_table(table)
        )
        if output_file:
            Path(output_file).write_text(report)
        return report


def main() -> None:
    """Run a demonstration of the PSA analysis."""
    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize analyzer
        analyzer = PSAAnalyzer(data_manager)

        # Generate report
        report = analyzer.generate_psa_report()
        logger.info("%s", report)

    except Exception:
        logger.exception("Error in PSA analysis")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
