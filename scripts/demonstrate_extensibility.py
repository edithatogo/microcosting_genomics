#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to demonstrate the Extensibility Framework."""

import logging
import sys
import traceback
from pathlib import Path

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.extensibility_framework import (
    ExampleAnalysisExtension,
    ExampleVisualizationExtension,
    ExtensibilityFramework,
)

logger = logging.getLogger(__name__)


def _write_demonstration_report(
    extensions: list[dict],
    result: object,
    viz_result: object,
    dependency_issues: dict,
) -> None:
    report = []
    report.append("# Extensibility Framework Demonstration Report\n")
    report.append("## Summary\n")
    report.append(
        "This report demonstrates the capabilities of the extensibility framework.\n",
    )

    report.append("## Registered Extensions\n")
    for extension in extensions:
        report.append(f"- **{extension['name']}** v{extension['version']}")
        report.append(f"  - Description: {extension['description']}")
        report.append(f"  - Type: {extension['type']}")
        report.append(f"  - Author: {extension['author']}")
        report.append(f"  - License: {extension['license']}")
        report.append(f"  - Enabled: {extension['enabled']}")
        report.append("")

    report.append("## Extension Execution Results\n")
    report.append(f"Analysis result: {result}\n")
    report.append(f"Visualization result: {viz_result}\n")

    report.append("## Dependency Validation\n")
    if dependency_issues:
        report.append("Dependency issues found:")
        for ext_name, missing_deps in dependency_issues.items():
            report.append(f"- {ext_name}: missing {missing_deps}")
    else:
        report.append("All extension dependencies are satisfied.")

    report_str = "\n".join(report)
    sys.stdout.write(str("\n" + report_str) + "\n")

    # Save report to file
    output_file = (
        Path(__file__).resolve().parents[1]
        / "reports"
        / "extensibility_framework_demo.md"
    )
    with Path(output_file).open("w") as f:
        f.write(report_str)
    sys.stdout.write(f"\nReport saved to {output_file}" + "\n")


def main() -> None:
    """Demonstrate the extensibility framework."""
    sys.stdout.write("Demonstrating Extensibility Framework..." + "\n")

    try:
        # Create data manager
        data_manager = DataManager()

        # Create extensibility framework
        framework = ExtensibilityFramework()
        framework.set_data_manager(data_manager)

        # Register example extensions
        analysis_extension = ExampleAnalysisExtension()
        viz_extension = ExampleVisualizationExtension()

        framework.register_extension(analysis_extension)
        framework.register_extension(viz_extension)

        # List extensions
        extensions = framework.list_extensions()
        sys.stdout.write(f"\nRegistered extensions: {len(extensions)}" + "\n")
        for extension in extensions:
            sys.stdout.write(
                "  - "
                f"{extension['name']}"
                " v"
                f"{extension['version']}"
                ": "
                f"{extension['description']}"
                "\n",
            )
            sys.stdout.write(f"    Type: {extension['type']}" + "\n")
            sys.stdout.write(f"    Author: {extension['author']}" + "\n")
            sys.stdout.write(f"    License: {extension['license']}" + "\n")
            sys.stdout.write(f"    Tags: {extension['tags']}" + "\n")
            sys.stdout.write(f"    Enabled: {extension['enabled']}" + "\n")
            sys.stdout.write("\n")

        # Execute extension methods
        sys.stdout.write("Executing extension methods..." + "\n")
        try:
            result = framework.execute_extension_method(
                "example_analysis_extension",
                "analyze",
                "test data",
            )
            sys.stdout.write(f"Analysis result: {result}" + "\n")

            viz_result = framework.execute_extension_method(
                "example_visualization_extension",
                "visualize",
                "test data",
            )
            sys.stdout.write(f"Visualization result: {viz_result}" + "\n")
        except Exception as e:
            logger.exception("Could not complete demonstrate extensibility")
            sys.stdout.write(f"Error executing extension method: {e}" + "\n")

        # Get extensions by type
        sys.stdout.write("\nExtensions by type:" + "\n")
        analysis_extensions = framework.get_extensions_by_type("analysis")
        sys.stdout.write(f"Analysis extensions: {len(analysis_extensions)}" + "\n")

        visualization_extensions = framework.get_extensions_by_type("visualization")
        sys.stdout.write(
            f"Visualization extensions: {len(visualization_extensions)}" + "\n",
        )

        # Validate dependencies
        sys.stdout.write("\nValidating extension dependencies..." + "\n")
        dependency_issues = framework.validate_extension_dependencies()
        if dependency_issues:
            sys.stdout.write("Dependency issues found:" + "\n")
            for ext_name, missing_deps in dependency_issues.items():
                sys.stdout.write(f"  {ext_name}: missing {missing_deps}" + "\n")
        else:
            sys.stdout.write("All extension dependencies are satisfied." + "\n")

        # Generate framework report
        _write_demonstration_report(extensions, result, viz_result, dependency_issues)

        # Cleanup
        framework.cleanup()
        sys.stdout.write("\nDemonstration complete." + "\n")

    except Exception as e:
        logger.exception("Could not complete demonstrate extensibility")
        sys.stdout.write(f"Error in extensibility framework demonstration: {e}" + "\n")

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
