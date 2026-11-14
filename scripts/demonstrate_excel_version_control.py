#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to demonstrate the Excel workbook version control system."""

import sys
import tempfile
from pathlib import Path

import pandas as pd

from genomics_microcosting.excel_version_control import WorkbookVersionControl


def create_sample_workbook(file_path: Path, data: dict) -> None:
    """Create a sample Excel workbook with the given data.

    Args:
        file_path (Path): Path where to save the workbook
        data (dict): Data to include in the workbook

    """
    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)


def main() -> int:
    """Demonstrate the Excel version control system."""
    sys.stdout.write("Excel Workbook Version Control System Demonstration" + "\n")
    sys.stdout.write(str("=" * 50) + "\n")

    # Create a temporary directory for our repository
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "excel_repo"
        sys.stdout.write(f"Creating repository at: {repo_dir}" + "\n")

        # Initialize version control
        vc = WorkbookVersionControl(repo_dir)

        # Create a sample workbook
        workbook_file = Path(temp_dir) / "sample_workbook.xlsx"
        sys.stdout.write(f"\n1. Creating sample workbook: {workbook_file}" + "\n")

        # Initial version
        data_v1 = {
            "item": ["Reagent A", "Reagent B", "Reagent C"],
            "quantity": [10, 5, 8],
            "unit_cost_aud_per_unit": [25.50, 15.75, 30.00],
            "total_cost_aud": [255.00, 78.75, 240.00],
        }
        create_sample_workbook(workbook_file, data_v1)

        # Commit first version
        sys.stdout.write("2. Committing first version of the workbook" + "\n")
        version_id_1 = vc.commit_workbook(
            workbook_file,
            metadata={
                "author": "Demo User",
                "description": "Initial version of sample workbook",
                "version": "1.0",
            },
        )
        sys.stdout.write(f"   Committed with version ID: {version_id_1}" + "\n")

        # Modify the workbook
        sys.stdout.write("\n3. Modifying the workbook" + "\n")
        data_v2 = {
            "item": ["Reagent A", "Reagent B", "Reagent C", "Reagent D"],
            "quantity": [10, 5, 8, 12],
            "unit_cost_aud_per_unit": [25.50, 15.75, 30.00, 22.50],
            "total_cost_aud": [255.00, 78.75, 240.00, 270.00],
        }
        create_sample_workbook(workbook_file, data_v2)

        # Commit second version
        sys.stdout.write("4. Committing updated version of the workbook" + "\n")
        version_id_2 = vc.commit_workbook(
            workbook_file,
            metadata={
                "author": "Demo User",
                "description": "Added Reagent D",
                "version": "1.1",
            },
        )
        sys.stdout.write(f"   Committed with version ID: {version_id_2}" + "\n")

        # List workbooks
        sys.stdout.write("\n5. Listing tracked workbooks" + "\n")
        workbooks = vc.list_workbooks()
        for workbook in workbooks:
            sys.stdout.write(f"   - {workbook}" + "\n")

        # Get workbook info
        sys.stdout.write("\n6. Getting workbook information" + "\n")
        info = vc.get_workbook_info("sample_workbook")
        sys.stdout.write(f"   Workbook: {info['workbook_name']}" + "\n")
        sys.stdout.write(f"   Versions: {info['version_count']}" + "\n")
        sys.stdout.write(f"   Latest: {info['latest_version']}" + "\n")

        # Compare versions
        sys.stdout.write("\n7. Comparing versions" + "\n")
        comparison = vc.compare_versions("sample_workbook", version_id_1, version_id_2)
        sys.stdout.write(f"   Same checksum: {comparison['same_checksum']}" + "\n")
        if "differences" in comparison:
            sys.stdout.write(f"   Differences: {comparison['differences']}" + "\n")

        # Verify integrity
        sys.stdout.write("\n8. Verifying workbook integrity" + "\n")
        is_valid = vc.verify_integrity("sample_workbook")
        sys.stdout.write(f"   Integrity check passed: {is_valid}" + "\n")

        # Checkout a specific version
        sys.stdout.write("\n9. Checking out a specific version" + "\n")
        checkout_path = Path(temp_dir) / "checked_out_version.xlsx"
        checked_out_file = vc.checkout_workbook(
            "sample_workbook",
            version_id_1,
            output_path=checkout_path,
        )
        sys.stdout.write(f"   Checked out version to: {checked_out_file}" + "\n")

        # Read and display the checked out data
        checked_out_data = pd.read_excel(checked_out_file)
        sys.stdout.write("   Content of checked out version:" + "\n")
        sys.stdout.write(str(checked_out_data.to_string(index=False)) + "\n")

        sys.stdout.write(str("\n" + "=" * 50) + "\n")
        sys.stdout.write("Demonstration completed successfully!" + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
