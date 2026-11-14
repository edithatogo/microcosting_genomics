#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to run scenario analysis for microcosting data."""

import argparse
import logging
import sys
import traceback
from pathlib import Path

from genomics_microcosting.scenario_modeling import (
    ScenarioManager,
    create_common_scenarios,
)
from genomics_microcosting.visualization import load_prepared_data

logger = logging.getLogger(__name__)


def _compare_requested_scenarios(
    scenario_manager: ScenarioManager,
    names: list[str],
    output_dir: Path,
) -> None:
    sys.stdout.write(f"Comparing scenarios: {names}\n")
    try:
        comparison = scenario_manager.compare_scenarios(
            names,
            "detailed_table",
        )

        # Save comparison to CSV
        comparison_file = output_dir / "scenario_comparison.csv"
        comparison.to_csv(comparison_file, index=False)
        sys.stdout.write(f"Saved comparison to {comparison_file}" + "\n")

        # Print summary
        sys.stdout.write("\nScenario Comparison Summary:" + "\n")
        sys.stdout.write(str(comparison.to_string(index=False)) + "\n")

    except Exception as e:
        logger.exception("Could not complete run scenario analysis")
        sys.stdout.write(f"Error comparing scenarios: {e}" + "\n")


def main() -> int:
    """Run scenario analysis."""
    parser = argparse.ArgumentParser(
        description="Run scenario analysis for microcosting data",
    )
    parser.add_argument("--data-dir", help="Path to prepared data directory")
    parser.add_argument("--output-dir", help="Path to output directory for results")
    parser.add_argument(
        "--scenario",
        help="Specific scenario to run (default: run all common scenarios)",
    )
    parser.add_argument("--compare", nargs="+", help="Scenarios to compare")

    args = parser.parse_args()

    sys.stdout.write("Running scenario analysis..." + "\n")

    try:
        # Load data
        if args.data_dir:
            data_dir = Path(args.data_dir)
        else:
            data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"

        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = Path(__file__).resolve().parents[1] / "reports" / "scenarios"

        output_dir.mkdir(parents=True, exist_ok=True)

        sys.stdout.write(f"Loading data from {data_dir}" + "\n")
        data_dict = load_prepared_data(data_dir)
        sys.stdout.write(f"Loaded {len(data_dict)} data tables" + "\n")

        # Create scenario manager
        scenario_manager = ScenarioManager(data_dict)

        # Add common scenarios
        common_scenarios = create_common_scenarios()
        for scenario in common_scenarios.values():
            scenario_manager.add_scenario(scenario)

        # Determine which scenarios to run
        if args.scenario:
            scenarios_to_run = [args.scenario]
        else:
            scenarios_to_run = list(common_scenarios.keys())

        # Run scenarios
        sys.stdout.write(f"Running scenarios: {scenarios_to_run}" + "\n")
        for scenario_name in scenarios_to_run:
            if scenario_name in scenario_manager.scenarios:
                sys.stdout.write(f"Running scenario: {scenario_name}" + "\n")
                results = scenario_manager.run_scenario_analysis(scenario_name)
                sys.stdout.write(f"  Processed {len(results)} tables" + "\n")
            else:
                sys.stdout.write(
                    f"Warning: Scenario '{scenario_name}' not found" + "\n",
                )

        if args.compare and "detailed_table" in data_dict:
            _compare_requested_scenarios(scenario_manager, args.compare, output_dir)

        # Generate report
        report_file = output_dir / "scenario_analysis_report.md"
        sys.stdout.write(f"Generating report in {report_file}" + "\n")
        scenario_manager.generate_scenario_report(scenarios_to_run, report_file)

        sys.stdout.write("Scenario analysis complete!" + "\n")
        sys.stdout.write(f"Results saved to {output_dir}" + "\n")

    except Exception as e:
        logger.exception("Could not complete run scenario analysis")
        sys.stdout.write(f"Error running scenario analysis: {e}" + "\n")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
