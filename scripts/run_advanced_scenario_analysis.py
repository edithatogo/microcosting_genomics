#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to run advanced scenario analysis with sophisticated comparison features."""

import argparse
import logging
import sys
import traceback
from pathlib import Path

from genomics_microcosting.advanced_scenario_modeling import (
    AdvancedScenarioManager,
    create_advanced_scenarios,
)
from genomics_microcosting.visualization import load_prepared_data

logger = logging.getLogger(__name__)


def _run_sensitivity(
    scenario_manager: AdvancedScenarioManager,
    scenarios_to_run: list[str],
    args: argparse.Namespace,
) -> None:
    # Run sensitivity analysis if requested
    if args.sensitivity:
        sys.stdout.write("Running sensitivity analysis..." + "\n")
        for scenario_name in scenarios_to_run:
            if scenario_name in scenario_manager.advanced_scenarios:
                scenario = scenario_manager.advanced_scenarios[scenario_name]
                if scenario.sensitivity_parameters:
                    for param, (
                        param_min,
                        param_max,
                    ) in scenario.sensitivity_parameters.items():
                        sys.stdout.write(
                            f"  Analyzing sensitivity for {param} in {scenario_name}\n",
                        )
                        try:
                            scenario_manager.run_sensitivity_analysis(
                                scenario_name,
                                param,
                                param_min,
                                param_max,
                                10,
                            )
                            sys.stdout.write(
                                f"    Sensitivity analysis for {param} completed\n",
                            )
                        except Exception as e:
                            logger.exception(
                                "Could not complete run advanced scenario analysis",
                            )
                            sys.stdout.write(
                                f"    Error in sensitivity analysis for {param}: {e}\n",
                            )
                else:
                    sys.stdout.write(
                        f"  No sensitivity parameters defined for {scenario_name}\n",
                    )


def _run_probabilistic(
    scenario_manager: AdvancedScenarioManager,
    scenarios_to_run: list[str],
    args: argparse.Namespace,
) -> None:
    # Run probabilistic analysis if requested
    if args.probabilistic:
        sys.stdout.write("Running probabilistic analysis..." + "\n")
        for scenario_name in scenarios_to_run:
            if scenario_name in scenario_manager.advanced_scenarios:
                sys.stdout.write(
                    f"  Running Monte Carlo simulation for {scenario_name}" + "\n",
                )
                try:
                    prob_results = scenario_manager.run_probabilistic_analysis(
                        scenario_name,
                        iterations=100,
                    )
                    sys.stdout.write(
                        "    Probabilistic analysis for "
                        f"{scenario_name}"
                        " completed with "
                        f"{len(prob_results)}"
                        " iterations"
                        "\n",
                    )
                except Exception as e:
                    logger.exception(
                        "Could not complete run advanced scenario analysis",
                    )
                    sys.stdout.write(
                        "    Error in probabilistic analysis for "
                        f"{scenario_name}"
                        ": "
                        f"{e}"
                        "\n",
                    )


def _compare_scenarios(
    scenario_manager: AdvancedScenarioManager,
    data_dict: dict,
    output_dir: Path,
    args: argparse.Namespace,
) -> None:
    # Compare scenarios if requested
    if args.compare:
        sys.stdout.write(f"Comparing scenarios: {args.compare}" + "\n")
        # Compare scenarios for the detailed table
        if "detailed_table" in data_dict:
            try:
                detailed_comparison = scenario_manager.compare_scenarios_detailed(
                    args.compare,
                    "detailed_table",
                )

                # Save detailed comparison to files
                comparison_dir = output_dir / "detailed_comparisons"
                comparison_dir.mkdir(exist_ok=True)

                for column, df in detailed_comparison.items():
                    # Sanitize column name for filename
                    safe_column = "".join(
                        c for c in column if c.isalnum() or c in (" ", "-", "_")
                    ).rstrip()
                    safe_column = safe_column.replace(" ", "_").replace(
                        "/",
                        "_per_",
                    )

                    # Save as CSV
                    csv_file = comparison_dir / f"detailed_comparison_{safe_column}.csv"
                    df.to_csv(csv_file)

                    # Save as JSON
                    json_file = (
                        comparison_dir / f"detailed_comparison_{safe_column}.json"
                    )
                    df.to_json(json_file, indent=2)

                sys.stdout.write(
                    f"Saved detailed comparisons to {comparison_dir}" + "\n",
                )

            except Exception as e:
                logger.exception("Could not complete run advanced scenario analysis")
                sys.stdout.write(f"Error in detailed comparison: {e}" + "\n")


def _export_results(
    scenario_manager: AdvancedScenarioManager,
    scenarios_to_run: list[str],
    output_dir: Path,
    args: argparse.Namespace,
) -> None:
    # Export results if requested
    sys.stdout.write(f"Exporting results in formats: {args.export_formats}" + "\n")
    for scenario_name in scenarios_to_run:
        if scenario_name in scenario_manager.results:
            try:
                scenario_manager.export_scenario_results(
                    scenario_name,
                    output_dir / "exported_results" / scenario_name,
                    formats=args.export_formats,
                )
                sys.stdout.write(f"  Exported results for {scenario_name}" + "\n")
            except Exception as e:
                logger.exception("Could not complete run advanced scenario analysis")
                sys.stdout.write(
                    f"  Error exporting results for {scenario_name}: {e}" + "\n",
                )


def _write_scenario_report(
    scenario_manager: AdvancedScenarioManager,
    scenarios_to_run: list[str],
    output_dir: Path,
) -> None:
    # Generate advanced report
    report_file = output_dir / "advanced_scenario_analysis_report.md"
    sys.stdout.write(f"Generating advanced report in {report_file}" + "\n")
    try:
        scenario_manager.generate_advanced_report(
            scenarios_to_run,
            str(report_file),
        )
        sys.stdout.write("Advanced report generated successfully" + "\n")
    except Exception as e:
        logger.exception("Could not complete run advanced scenario analysis")
        sys.stdout.write(f"Error generating advanced report: {e}" + "\n")
        # Generate a simpler report as fallback
        fallback_report = output_dir / "scenario_analysis_report.md"
        sys.stdout.write(f"Generating fallback report in {fallback_report}" + "\n")
        scenario_manager.generate_scenario_report(
            scenarios_to_run,
            str(fallback_report),
        )


def main() -> int:
    """Run advanced scenario analysis."""
    parser = argparse.ArgumentParser(
        description="Run advanced scenario analysis for microcosting data",
    )
    parser.add_argument("--data-dir", help="Path to prepared data directory")
    parser.add_argument("--output-dir", help="Path to output directory for results")
    parser.add_argument(
        "--scenario",
        help="Specific scenario to run (default: run all advanced scenarios)",
    )
    parser.add_argument("--compare", nargs="+", help="Scenarios to compare")
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help="Run sensitivity analysis",
    )
    parser.add_argument(
        "--probabilistic",
        action="store_true",
        help="Run probabilistic analysis",
    )
    parser.add_argument(
        "--export-formats",
        nargs="+",
        default=["csv"],
        help="Formats to export results (csv, json, parquet)",
    )

    args = parser.parse_args()

    sys.stdout.write("Running advanced scenario analysis..." + "\n")

    try:
        # Load data
        root = Path(__file__).resolve().parents[1]
        data_dir = Path(args.data_dir) if args.data_dir else root / "data" / "prepared"
        output_dir = (
            Path(args.output_dir)
            if args.output_dir
            else root / "reports" / "advanced_scenarios"
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        sys.stdout.write(f"Loading data from {data_dir}" + "\n")
        data_dict = load_prepared_data(data_dir)
        sys.stdout.write(f"Loaded {len(data_dict)} data tables" + "\n")

        # Create advanced scenario manager
        scenario_manager = AdvancedScenarioManager(data_dict)

        # Add advanced scenarios
        advanced_scenarios = create_advanced_scenarios()
        for scenario in advanced_scenarios.values():
            scenario_manager.add_advanced_scenario(scenario)

        # Determine which scenarios to run
        if args.scenario:
            scenarios_to_run = [args.scenario]
        else:
            scenarios_to_run = list(advanced_scenarios.keys())

        # Run scenarios
        sys.stdout.write(f"Running scenarios: {scenarios_to_run}" + "\n")
        for scenario_name in scenarios_to_run:
            if scenario_name in scenario_manager.advanced_scenarios:
                sys.stdout.write(f"Running scenario: {scenario_name}" + "\n")
                results = scenario_manager.run_scenario_analysis(scenario_name)
                sys.stdout.write(f"  Processed {len(results)} tables" + "\n")
            else:
                sys.stdout.write(
                    f"Warning: Scenario '{scenario_name}' not found" + "\n",
                )

        _run_sensitivity(scenario_manager, scenarios_to_run, args)

        _run_probabilistic(scenario_manager, scenarios_to_run, args)

        _compare_scenarios(scenario_manager, data_dict, output_dir, args)

        _export_results(scenario_manager, scenarios_to_run, output_dir, args)

        _write_scenario_report(scenario_manager, scenarios_to_run, output_dir)

        sys.stdout.write("Advanced scenario analysis complete!" + "\n")
        sys.stdout.write(f"Results saved to {output_dir}" + "\n")

        sys.stdout.write("\nGenerated files:\n")
        sys.stdout.writelines(
            f"  {item.relative_to(output_dir)}\n"
            for item in output_dir.rglob("*")
            if item.is_file()
        )

    except Exception as e:
        logger.exception("Could not complete run advanced scenario analysis")
        sys.stdout.write(f"Error running advanced scenario analysis: {e}" + "\n")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
