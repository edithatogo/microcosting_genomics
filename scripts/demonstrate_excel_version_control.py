#!/usr/bin/env python3
"""
Script to demonstrate the Excel workbook version control system.
"""

import sys
from pathlib import Path
import pandas as pd
import tempfile

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.excel_version_control import WorkbookVersionControl


def create_sample_workbook(file_path: Path, data: dict) -> None:
    """Create a sample Excel workbook with the given data.
    
    Args:
        file_path (Path): Path where to save the workbook
        data (dict): Data to include in the workbook
    """
    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)


def main():
    """Main function to demonstrate the Excel version control system."""
    print("Excel Workbook Version Control System Demonstration")
    print("=" * 50)
    
    # Create a temporary directory for our repository
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "excel_repo"
        print(f"Creating repository at: {repo_dir}")
        
        # Initialize version control
        vc = WorkbookVersionControl(repo_dir)
        
        # Create a sample workbook
        workbook_file = Path(temp_dir) / "sample_workbook.xlsx"
        print(f"\n1. Creating sample workbook: {workbook_file}")
        
        # Initial version
        data_v1 = {
            "Item": ["Reagent A", "Reagent B", "Reagent C"],
            "Quantity": [10, 5, 8],
            "Unit Cost": [25.50, 15.75, 30.00],
            "Total Cost": [255.00, 78.75, 240.00]
        }
        create_sample_workbook(workbook_file, data_v1)
        
        # Commit first version
        print("2. Committing first version of the workbook")
        version_id_1 = vc.commit_workbook(
            workbook_file,
            metadata={
                "author": "Demo User",
                "description": "Initial version of sample workbook",
                "version": "1.0"
            }
        )
        print(f"   Committed with version ID: {version_id_1}")
        
        # Modify the workbook
        print("\n3. Modifying the workbook")
        data_v2 = {
            "Item": ["Reagent A", "Reagent B", "Reagent C", "Reagent D"],
            "Quantity": [10, 5, 8, 12],
            "Unit Cost": [25.50, 15.75, 30.00, 22.50],
            "Total Cost": [255.00, 78.75, 240.00, 270.00]
        }
        create_sample_workbook(workbook_file, data_v2)
        
        # Commit second version
        print("4. Committing updated version of the workbook")
        version_id_2 = vc.commit_workbook(
            workbook_file,
            metadata={
                "author": "Demo User",
                "description": "Added Reagent D",
                "version": "1.1"
            }
        )
        print(f"   Committed with version ID: {version_id_2}")
        
        # List workbooks
        print("\n5. Listing tracked workbooks")
        workbooks = vc.list_workbooks()
        for workbook in workbooks:
            print(f"   - {workbook}")
        
        # Get workbook info
        print("\n6. Getting workbook information")
        info = vc.get_workbook_info("sample_workbook")
        print(f"   Workbook: {info['workbook_name']}")
        print(f"   Versions: {info['version_count']}")
        print(f"   Latest: {info['latest_version']}")
        
        # Compare versions
        print("\n7. Comparing versions")
        comparison = vc.compare_versions("sample_workbook", version_id_1, version_id_2)
        print(f"   Same checksum: {comparison['same_checksum']}")
        if 'differences' in comparison:
            print(f"   Differences: {comparison['differences']}")
        
        # Verify integrity
        print("\n8. Verifying workbook integrity")
        is_valid = vc.verify_integrity("sample_workbook")
        print(f"   Integrity check passed: {is_valid}")
        
        # Checkout a specific version
        print("\n9. Checking out a specific version")
        checkout_path = Path(temp_dir) / "checked_out_version.xlsx"
        checked_out_file = vc.checkout_workbook(
            "sample_workbook", 
            version_id_1, 
            output_path=checkout_path
        )
        print(f"   Checked out version to: {checked_out_file}")
        
        # Read and display the checked out data
        checked_out_data = pd.read_excel(checked_out_file)
        print("   Content of checked out version:")
        print(checked_out_data.to_string(index=False))
        
        print("\n" + "=" * 50)
        print("Demonstration completed successfully!")
        
    return 0


if __name__ == "__main__":
    sys.exit(main())