# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Monte Carlo Optimization module."""

import unittest
from concurrent.futures import Future
from copy import deepcopy
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import numpy as np

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.monte_carlo_optimizer import (
    DistributionSpec,
    MonteCarloOptimizer,
)
from tests.checks import require_close, require_runtime_instance

if TYPE_CHECKING:
    from collections.abc import Callable


class TestMonteCarloOptimizer(unittest.TestCase):
    """Test cases for the MonteCarloOptimizer class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_data_manager = Mock(spec=DataManager)
        self.optimizer = MonteCarloOptimizer(self.mock_data_manager)

    def test_init(self) -> None:
        """Test MonteCarloOptimizer initialization."""
        require_runtime_instance(self.optimizer, MonteCarloOptimizer)
        if not ((self.optimizer.data_manager) == (self.mock_data_manager)):
            raise AssertionError

    def test_vectorized_sampling_normal(self) -> None:
        """Test vectorized sampling from normal distribution."""
        parameters = {"mean": 100, "std": 15}
        size = 1000

        result = self.optimizer.vectorized_sampling("normal", parameters, size)

        require_runtime_instance(result, np.ndarray)
        if not ((len(result)) == (size)):
            raise AssertionError
        # Check that the mean and std are approximately correct
        require_close(np.mean(result), 100, delta=5)  # Allow some variance
        require_close(np.std(result), 15, delta=3)  # Allow some variance

    def test_vectorized_sampling_uniform(self) -> None:
        """Test vectorized sampling from uniform distribution."""
        parameters = {"low": 10, "high": 50}
        size = 1000

        result = self.optimizer.vectorized_sampling("uniform", parameters, size)

        require_runtime_instance(result, np.ndarray)
        if not ((len(result)) == (size)):
            raise AssertionError
        # Check that values are within expected range
        if not (np.all(result >= parameters["low"])):
            raise AssertionError
        if not (np.all(result <= parameters["high"])):
            raise AssertionError
        # Check that the mean is approximately correct
        require_close(np.mean(result), 30, delta=5)  # (10+50)/2 = 30

    def test_vectorized_sampling_triangular(self) -> None:
        """Test vectorized sampling from triangular distribution."""
        parameters = {"left": 0, "mode": 50, "right": 100}
        size = 1000

        result = self.optimizer.vectorized_sampling("triangular", parameters, size)

        require_runtime_instance(result, np.ndarray)
        if not ((len(result)) == (size)):
            raise AssertionError
        # Check that values are within expected range
        if not (np.all(result >= 0)):
            raise AssertionError
        if not (np.all(result <= parameters["right"])):
            raise AssertionError
        # Check the mean of this symmetric triangle (approximately 50).
        require_close(np.mean(result), 50, delta=10)

    def test_single_process_sampling(self) -> None:
        """Test single-process sampling."""
        parameters: dict[str, DistributionSpec] = {
            "param1": {
                "distribution": "normal",
                "parameters": {"mean": 100, "std": 15},
            },
            "param2": {
                "distribution": "uniform",
                "parameters": {"low": 10, "high": 50},
            },
        }
        iterations = 100

        result = self.optimizer.sample_parameters(parameters, iterations)

        require_runtime_instance(result, dict)
        if ("param1") not in (result):
            raise AssertionError
        if ("param2") not in (result):
            raise AssertionError
        require_runtime_instance(result["param1"], np.ndarray)
        require_runtime_instance(result["param2"], np.ndarray)
        if not ((len(result["param1"])) == (iterations)):
            raise AssertionError
        if not ((len(result["param2"])) == (iterations)):
            raise AssertionError

    def test_create_chunks(self) -> None:
        """Test chunk creation for parallel processing."""
        total_iterations = 100000
        chunk_size = 10000
        n_processes = 4

        chunks = self.optimizer.create_chunks(
            total_iterations,
            chunk_size,
            n_processes,
        )

        require_runtime_instance(chunks, list)
        if not ((len(chunks)) > (0)):
            raise AssertionError
        if not ((sum(chunks)) == (total_iterations)):
            raise AssertionError

    def test_optimized_cost_calculation(self) -> None:
        """Test optimized cost calculation."""
        # Create test simulation results
        simulation_results = {
            "param1": np.array([1, 2, 3, 4, 5]),
            "param2": np.array([10, 20, 30, 40, 50]),
        }

        # Define a simple cost function
        def cost_function(params: dict[str, float]) -> float:
            return params["param1"] + params["param2"]

        result = self.optimizer.optimized_cost_calculation(
            simulation_results,
            cost_function,
        )

        require_runtime_instance(result, np.ndarray)
        expected_length = 5
        if not ((len(result)) == (expected_length)):
            raise AssertionError
        # Check that the cost calculation is correct
        expected = np.array([11, 22, 33, 44, 55])
        np.testing.assert_array_equal(result, expected)

    def test_benchmark_sampling_methods(self) -> None:
        """Test benchmarking of sampling methods."""
        parameters: dict[str, DistributionSpec] = {
            "test_param": {
                "distribution": "normal",
                "parameters": {"mean": 0, "std": 1},
            },
        }
        iterations = 10000

        result = self.optimizer.benchmark_sampling_methods(parameters, iterations)

        require_runtime_instance(result, dict)
        if ("single_process_vectorized") not in (result):
            raise AssertionError
        if not ((result["single_process_vectorized"]) > (0)):
            raise AssertionError
        # Parallel sampling might not be benchmarked for small iterations
        # but should not raise an exception

    def test_sample_chunk(self) -> None:
        """Test sampling a chunk of data."""
        parameters: dict[str, DistributionSpec] = {
            "param1": {
                "distribution": "normal",
                "parameters": {"mean": 100, "std": 15},
            },
        }
        chunk_size = 100

        result = self.optimizer.sample_chunk(parameters, chunk_size)

        require_runtime_instance(result, dict)
        if ("param1") not in (result):
            raise AssertionError
        require_runtime_instance(result["param1"], list)
        if not ((len(result["param1"])) == (chunk_size)):
            raise AssertionError

    def test_generate_optimization_report(self) -> None:
        """Test optimization report generation."""
        # Generate report
        report = self.optimizer.generate_optimization_report()

        # Check that report is generated
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError
        if ("Monte Carlo Simulation Optimization") not in (report):
            raise AssertionError
        if ("Benchmark Results") not in (report):
            raise AssertionError
        if "5-10x" in report or "2-4x" in report:
            raise AssertionError


if __name__ == "__main__":
    unittest.main()


def test_single_process_sampling_keeps_caller_parameters() -> None:
    """Do not alter the input specification after its provenance is captured."""
    parameters: dict[str, DistributionSpec] = {
        "cost": {"distribution": "normal", "parameters": {"mean": 4.0, "std": 1.0}},
    }
    before = deepcopy(parameters)
    optimizer = MonteCarloOptimizer(Mock(spec=DataManager))
    iterations = 7
    result = optimizer.sample_parameters(parameters, iterations)
    if parameters != before:
        raise AssertionError
    if len(result["cost"]) != iterations:
        raise AssertionError


def test_parallel_dispatch_conserves_requested_iteration_count() -> None:
    """Exercise every dispatched chunk without replacing its sampling function."""
    parameters: dict[str, DistributionSpec] = {
        "cost": {"distribution": "normal", "parameters": {"mean": 4.0, "std": 1.0}},
    }
    iterations = 17
    optimizer = MonteCarloOptimizer(Mock(spec=DataManager), seed=42)
    dispatched: list[list[float]] = []

    def submit(
        operation: Callable[
            [dict[str, DistributionSpec], int, np.random.SeedSequence],
            dict[str, list[float]],
        ],
        values: dict[str, DistributionSpec],
        size: int,
        seed: np.random.SeedSequence,
    ) -> Future[dict[str, list[float]]]:
        future: Future[dict[str, list[float]]] = Future()
        samples = operation(values, size, seed)
        dispatched.append(samples["cost"])
        future.set_result(samples)
        return future

    with patch(
        "genomics_microcosting.monte_carlo_optimizer.ProcessPoolExecutor",
    ) as factory:
        factory.return_value.__enter__.return_value.submit.side_effect = submit
        result = optimizer.parallel_monte_carlo_simulation(
            parameters,
            iterations=iterations,
            n_processes=2,
            chunk_size=4,
        )
    if len(result["cost"]) != iterations:
        raise AssertionError
    if not dispatched or result["cost"].tolist() != [
        sample for chunk in dispatched for sample in chunk
    ]:
        raise AssertionError
    if len({chunk[0] for chunk in dispatched}) != len(dispatched):
        raise AssertionError
