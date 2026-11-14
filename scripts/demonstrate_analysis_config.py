#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to demonstrate the Configuration-driven Analysis Parameters System."""

import logging
import sys
import traceback
from pathlib import Path

from genomics_microcosting.analysis_config import AnalysisConfigurationManager

logger = logging.getLogger(__name__)

REPORT_PREVIEW_LIMIT = 1000


def main() -> None:
    """Demonstrate the analysis configuration system."""
    sys.stdout.write(
        "Demonstrating Configuration-driven Analysis Parameters System..." + "\n",
    )

    try:
        # Create configuration manager
        config_manager = AnalysisConfigurationManager()

        # List available configurations
        sys.stdout.write("\nAvailable configurations:" + "\n")
        config_names = config_manager.list_configurations()
        for name in config_names:
            sys.stdout.write(f"  - {name}" + "\n")

        # Show details for a few configurations
        sys.stdout.write("\nConfiguration details:" + "\n")
        for config_name in ["cost_driver_analysis", "psa_analysis", "voi_analysis"]:
            config = config_manager.get_configuration(config_name)
            if config:
                sys.stdout.write(f"\n{config_name}:" + "\n")
                sys.stdout.write(f"  Description: {config.description}" + "\n")
                sys.stdout.write(f"  Version: {config.version}" + "\n")
                sys.stdout.write(f"  Author: {config.author}" + "\n")
                sys.stdout.write(f"  Parameters ({len(config.parameters)}):" + "\n")
                for param_name, parameter in config.parameters.items():
                    sys.stdout.write(
                        f"    {param_name}: {parameter.value} ({parameter.description})"
                        "\n",
                    )

        # Demonstrate parameter access
        sys.stdout.write("\nParameter access examples:" + "\n")
        top_n_drivers = config_manager.get_parameter_value(
            "cost_driver_analysis",
            "top_n_drivers",
            10,
        )
        sys.stdout.write(f"Cost driver analysis top_n_drivers: {top_n_drivers}" + "\n")

        monte_carlo_iterations = config_manager.get_parameter_value(
            "psa_analysis",
            "monte_carlo_iterations",
            1000,
        )
        sys.stdout.write(
            f"PSA analysis monte_carlo_iterations: {monte_carlo_iterations}" + "\n",
        )

        # Demonstrate parameter modification
        sys.stdout.write("\nParameter modification examples:" + "\n")
        success = config_manager.set_parameter_value(
            "cost_driver_analysis",
            "top_n_drivers",
            15,
        )
        sys.stdout.write(
            f"Setting top_n_drivers to 15: {'Success' if success else 'Failed'}" + "\n",
        )

        new_value = config_manager.get_parameter_value(
            "cost_driver_analysis",
            "top_n_drivers",
        )
        sys.stdout.write(f"New value of top_n_drivers: {new_value}" + "\n")

        # Demonstrate validation
        sys.stdout.write("\nConfiguration validation:" + "\n")
        validation_results = config_manager.validate_configuration(
            "cost_driver_analysis",
        )
        if validation_results["errors"]:
            sys.stdout.write("Errors found:" + "\n")
            for error in validation_results["errors"]:
                sys.stdout.write(f"  - {error}" + "\n")
        else:
            sys.stdout.write("No validation errors found." + "\n")

        if validation_results["warnings"]:
            sys.stdout.write("Warnings found:" + "\n")
            for warning in validation_results["warnings"]:
                sys.stdout.write(f"  - {warning}" + "\n")

        # Generate configuration report
        report = config_manager.generate_config_report()
        sys.stdout.write(str("\n" + "=" * 50) + "\n")
        sys.stdout.write("CONFIGURATION REPORT" + "\n")
        sys.stdout.write(str("=" * 50) + "\n")
        sys.stdout.write(
            str(report[:1000] + "..." if len(report) > REPORT_PREVIEW_LIMIT else report)
            + "\n",
        )  # Show first 1000 chars

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[1]
            / "reports"
            / "analysis_configuration_demo.md"
        )
        config_manager.generate_config_report(output_file=str(output_file))
        sys.stdout.write(f"\nReport saved to {output_file}" + "\n")

        sys.stdout.write("\nDemonstration complete." + "\n")

    except Exception as e:
        logger.exception("Could not complete demonstrate analysis config")
        sys.stdout.write(f"Error in analysis configuration demonstration: {e}" + "\n")

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
