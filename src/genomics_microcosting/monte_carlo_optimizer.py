# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Monte Carlo Simulation Optimization module for microcosting analysis.

This module provides optimized implementations for Monte Carlo simulations
to improve computational efficiency in probabilistic sensitivity analysis.
"""

import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import numpy as np

from .data_manager import DataManager
from .logging_config import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from numpy.typing import NDArray

logger = get_logger(__name__)

PARALLEL_BENCHMARK_THRESHOLD = 10000


class DistributionSpec(TypedDict, total=False):
    """The existing distribution name and numeric parameters supplied by callers."""

    distribution: str
    parameters: Mapping[str, float]


class MonteCarloOptimizer:
    """Optimizer for Monte Carlo simulations to improve computational efficiency."""

    def __init__(
        self,
        data_manager: DataManager,
        *,
        seed: int | None = None,
    ) -> None:
        """Initialize the MonteCarloOptimizer.

        Args:
            data_manager: DataManager instance for accessing prepared data
            seed: Optional seed for repeatable draws and independent worker streams

        """
        self.data_manager = data_manager
        self._seed_sequence = np.random.SeedSequence(seed)
        self._rng = np.random.default_rng(self._seed_sequence.spawn(1)[0])
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    def vectorized_sampling(
        self,
        distribution_type: str,
        parameters: Mapping[str, float],
        size: int,
    ) -> NDArray[np.float64]:
        """Sample values using vectorized operations for improved performance.

        Args:
            distribution_type: Distribution name, such as normal or uniform.
            parameters: Dictionary of distribution parameters
            size: Number of samples to generate

        Returns:
            Array of sampled values

        """
        self.logger.debug(
            "Vectorized sampling %s values from %s distribution",
            size,
            distribution_type,
        )

        if distribution_type == "normal":
            mean = parameters.get("mean", 0)
            std = parameters.get("std", 1)
            return self._rng.normal(mean, std, size)
        if distribution_type == "uniform":
            low = parameters.get("low", 0)
            high = parameters.get("high", 1)
            return self._rng.uniform(low, high, size)
        if distribution_type == "triangular":
            left = parameters.get("left", 0)
            mode = parameters.get("mode", 0.5)
            right = parameters.get("right", 1)
            return self._rng.triangular(left, mode, right, size)
        if distribution_type == "lognormal":
            mean = parameters.get("mean", 0)
            sigma = parameters.get("sigma", 1)
            return self._rng.lognormal(mean, sigma, size)
        if distribution_type == "exponential":
            scale = parameters.get("scale", 1)
            return self._rng.exponential(scale, size)
        # Default to normal distribution
        mean = parameters.get("mean", 0)
        std = parameters.get("std", 1)
        return self._rng.normal(mean, std, size)

    def parallel_monte_carlo_simulation(
        self,
        parameters: Mapping[str, DistributionSpec],
        iterations: int = 1000,
        n_processes: int | None = None,
        chunk_size: int = 10000,
    ) -> dict[str, NDArray[np.float64]]:
        """Perform Monte Carlo simulation using parallel processing.

        Args:
            parameters: Dictionary mapping parameter names to distribution info
            iterations: Number of Monte Carlo iterations
            n_processes: Number of processes to use (None for auto-detection)
            chunk_size: Size of chunks for parallel processing

        Returns:
            Dictionary of simulation results

        """
        self.logger.info(
            "Performing parallel Monte Carlo simulation with %s iterations...",
            iterations,
        )

        if n_processes is None:
            n_processes = min(mp.cpu_count(), 4)  # Limit to 4 processes max

        self.logger.info("Using %s processes for parallel computation", n_processes)

        # If iterations are small, just use vectorized sampling
        if iterations <= chunk_size:
            return self._single_process_sampling(parameters, iterations)

        # For large iterations, use parallel processing
        chunks = self._create_chunks(iterations, chunk_size, n_processes)

        # Prepare arguments for parallel processing
        worker_args = zip(
            chunks,
            self._seed_sequence.spawn(len(chunks)),
            strict=True,
        )

        results: dict[str, NDArray[np.float64]] = {}

        try:
            with ProcessPoolExecutor(max_workers=n_processes) as executor:
                # Submit all tasks
                futures = [
                    executor.submit(self._sample_chunk, parameters, size, seed)
                    for size, seed in worker_args
                ]

                # Collect results
                collected_results: dict[str, list[float]] = {}
                for future in futures:
                    chunk_results = future.result()
                    for param_name, samples in chunk_results.items():
                        if param_name not in collected_results:
                            collected_results[param_name] = []
                        collected_results[param_name].extend(samples)

                # Convert to numpy arrays
                for param_name, samples_list in collected_results.items():
                    results[param_name] = np.array(samples_list)

        except Exception as e:
            self.logger.warning(
                "Parallel processing failed: %s. Falling back to single process.",
                e,
                exc_info=True,
            )
            return self._single_process_sampling(parameters, iterations)

        return results

    def _single_process_sampling(
        self,
        parameters: Mapping[str, DistributionSpec],
        iterations: int,
    ) -> dict[str, NDArray[np.float64]]:
        """Retain the existing internal hook through the public checked boundary."""
        return self.sample_parameters(parameters, iterations)

    def sample_parameters(
        self,
        parameters: Mapping[str, DistributionSpec],
        iterations: int,
    ) -> dict[str, NDArray[np.float64]]:
        """Perform sampling in a single process.

        Args:
            parameters: Dictionary mapping parameter names to distribution info
            iterations: Number of iterations

        Returns:
            Dictionary of simulation results

        """
        results: dict[str, NDArray[np.float64]] = {}

        for param_name, param_info in parameters.items():
            dist_type = param_info.get("distribution", "normal")
            dist_params = param_info.get("parameters", {})

            samples = self.vectorized_sampling(dist_type, dist_params, iterations)
            results[param_name] = samples

        return results

    def _sample_chunk(
        self,
        parameters: Mapping[str, DistributionSpec],
        chunk_size: int,
        seed: np.random.SeedSequence | None = None,
    ) -> dict[str, list[float]]:
        """Retain the existing internal hook through the public checked boundary."""
        if seed is not None:
            # Each submitted task deserializes its own optimizer and seed.
            self._rng = np.random.default_rng(seed)
        return self.sample_chunk(parameters, chunk_size)

    def sample_chunk(
        self,
        parameters: Mapping[str, DistributionSpec],
        chunk_size: int,
    ) -> dict[str, list[float]]:
        """Sample a chunk of data for parallel processing.

        Args:
            parameters: Dictionary mapping parameter names to distribution info
            chunk_size: Size of the chunk to sample

        Returns:
            Dictionary of sampled values as lists

        """
        chunk_results: dict[str, list[float]] = {}

        for param_name, param_info in parameters.items():
            dist_type = param_info.get("distribution", "normal")
            dist_params = param_info.get("parameters", {})

            samples = self.vectorized_sampling(dist_type, dist_params, chunk_size)
            chunk_results[param_name] = (
                samples.tolist()
            )  # Convert to list for serialization

        return chunk_results

    def _create_chunks(
        self,
        total_iterations: int,
        chunk_size: int,
        n_processes: int,
    ) -> list[int]:
        """Retain the existing internal hook through the public checked boundary."""
        return self.create_chunks(total_iterations, chunk_size, n_processes)

    def create_chunks(
        self,
        total_iterations: int,
        chunk_size: int,
        n_processes: int,
    ) -> list[int]:
        """Create chunks for parallel processing.

        Args:
            total_iterations: Total number of iterations
            chunk_size: Size of each chunk
            n_processes: Number of processes

        Returns:
            List of chunk sizes

        """
        n_chunks = min(
            (total_iterations // chunk_size) + 1,
            n_processes * 4,
        )  # Limit chunks
        base_chunk_size = total_iterations // n_chunks
        remainder = total_iterations % n_chunks

        chunks = [base_chunk_size] * n_chunks
        # Distribute remainder
        for i in range(remainder):
            chunks[i] += 1

        return chunks

    def optimized_cost_calculation(
        self,
        simulation_results: dict[str, np.ndarray],
        cost_function: Callable[[dict[str, float]], float],
    ) -> NDArray[np.float64]:
        """Calculate cost outcomes using optimized vectorized operations.

        Args:
            simulation_results: Dictionary of parameter samples from simulation
            cost_function: Function that takes parameter dictionary and returns cost

        Returns:
            Array of cost outcomes

        """
        self.logger.info("Performing optimized cost calculation...")

        # Get the number of iterations
        n_iterations = len(next(iter(simulation_results.values())))

        # Vectorize the cost function
        cost_outcomes = np.zeros(n_iterations)

        # Process in chunks to manage memory
        chunk_size = 10000
        for i in range(0, n_iterations, chunk_size):
            end_idx = min(i + chunk_size, n_iterations)

            # Create parameter dictionaries for this chunk
            for j in range(i, end_idx):
                params: dict[str, float] = {
                    param_name: samples[j]
                    for param_name, samples in simulation_results.items()
                }
                cost_outcomes[j] = cost_function(params)

        return cost_outcomes

    def benchmark_sampling_methods(
        self,
        parameters: Mapping[str, DistributionSpec],
        iterations: int = 100000,
    ) -> dict[str, float]:
        """Benchmark different sampling methods for performance comparison.

        Args:
            parameters: Dictionary mapping parameter names to distribution info
            iterations: Number of iterations for benchmarking

        Returns:
            Dictionary of benchmark results (method name -> execution time)

        """
        self.logger.info(
            "Benchmarking sampling methods with %s iterations...",
            iterations,
        )

        results: dict[str, float] = {}

        # Benchmark single-process vectorized sampling
        start_time = time.time()
        self._single_process_sampling(parameters, iterations)
        results["single_process_vectorized"] = time.time() - start_time

        # Benchmark parallel sampling (if beneficial)
        # Only benchmark parallel for large iterations.
        if iterations > PARALLEL_BENCHMARK_THRESHOLD:
            start_time = time.time()
            n_processes = min(mp.cpu_count(), 4)
            self.parallel_monte_carlo_simulation(parameters, iterations, n_processes)
            results["parallel_sampling"] = time.time() - start_time
        else:
            results["parallel_sampling"] = float("inf")  # Not applicable

        return results

    def generate_optimization_report(self, output_file: str | None = None) -> str:
        """Generate a comprehensive optimization report.

        Args:
            output_file: Optional file path to save the report

        Returns:
            Report as a string

        """
        try:
            # Define test parameters for benchmarking
            test_parameters: dict[str, DistributionSpec] = {
                "labour_cost": {
                    "distribution": "normal",
                    "parameters": {"mean": 800, "std": 100},
                },
                "equipment_cost": {
                    "distribution": "triangular",
                    "parameters": {"left": 400, "mode": 600, "right": 1000},
                },
                "consumable_cost": {
                    "distribution": "uniform",
                    "parameters": {"low": 200, "high": 400},
                },
            }

            # Benchmark different methods
            small_benchmark = self.benchmark_sampling_methods(test_parameters, 10000)
            large_benchmark = self.benchmark_sampling_methods(test_parameters, 100000)

            # Generate report
            report: list[str] = []
            report.append("# Monte Carlo Simulation Optimization Report\n")
            report.append("## Executive Summary\n")
            report.append(
                "This report presents the results of computational efficiency "
                "optimizations "
                "for Monte Carlo simulations used in probabilistic sensitivity "
                "analysis.\n",
            )

            report.append("## Optimization Methods Implemented\n")
            report.append(
                "1. **Vectorized Sampling**: Using NumPy's vectorized operations "
                "for faster random sampling\n",
            )
            report.append(
                "2. **Parallel Processing**: Distributing computations across "
                "multiple CPU cores\n",
            )
            report.append(
                "3. **Memory Management**: Chunked processing to handle large "
                "datasets efficiently\n",
            )
            report.append(
                "4. **Adaptive Algorithm Selection**: Choosing the best method "
                "based on problem size\n",
            )

            report.append("\n## Benchmark Results (Small Scale: 10,000 iterations)\n")
            for method, exec_time in small_benchmark.items():
                if exec_time != float("inf"):
                    report.append(f"- {method}: {exec_time:.4f} seconds\n")

            report.append("\n## Benchmark Results (Large Scale: 100,000 iterations)\n")
            for method, exec_time in large_benchmark.items():
                if exec_time != float("inf"):
                    report.append(f"- {method}: {exec_time:.4f} seconds\n")

            report.extend(
                [
                    "\n## Interpretation limits\n",
                    (
                        "These timings describe the selected synthetic workload "
                        "on this runtime.\n"
                    ),
                    (
                        "No naive reference method was measured, so no speedup is "
                        "established.\n"
                    ),
                    (
                        "They do not establish study-level numerical or scientific "
                        "validity.\n"
                    ),
                    (
                        "Parallel fallback warnings must be reviewed before "
                        "interpreting timings.\n"
                    ),
                ],
            )

            report_str = "\n".join(report)

            if output_file:
                Path(output_file).write_text(report_str)

        except Exception:
            self.logger.exception("Error generating optimization report")
            raise
        else:
            return report_str


def main() -> None:
    """Run the synthetic Monte Carlo optimization demonstration."""
    try:
        # Initialize data manager
        data_manager = DataManager()

        # Initialize optimizer
        optimizer = MonteCarloOptimizer(data_manager)

        # Generate report
        report = optimizer.generate_optimization_report()
        sys.stdout.write(report + "\n")

    except Exception:
        logger.exception("Error in Monte Carlo optimization")
        raise


if __name__ == "__main__":
    main()
