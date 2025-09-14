#!/usr/bin/env python3
"""
Script to perform Data Consistency Validation on the microcosting model.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.data_consistency_validator import DataConsistencyValidator  # noqa: E402
from genomics_microcosting.data_manager import DataManager  # noqa: E402


def main():
    """Main function to run data consistency validation."""
    print("Running Data Consistency Validation...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize validator
        validator = DataConsistencyValidator(data_manager)
        
        # Generate report
        report = validator.generate_validation_report()
        print(report)
        
        # Save report to file
        output_file = Path(__file__).resolve().parents[1] / "reports" / "data_consistency_validation.md"
        validator.generate_validation_report(output_file=str(output_file))
        print(f"Report saved to {output_file}")
        
    except Exception as e:
        print(f"Error in data consistency validation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()