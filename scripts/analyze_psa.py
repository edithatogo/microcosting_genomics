#!/usr/bin/env python3
"""
Script to perform Probabilistic Sensitivity Analysis (PSA) on the microcosting model.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.psa_analysis import PSAAnalyzer  # noqa: E402
from genomics_microcosting.data_manager import DataManager  # noqa: E402


def main():
    """Main function to run PSA analysis."""
    print("Running Probabilistic Sensitivity Analysis (PSA)...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = PSAAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_psa_report(iterations=1000)
        print(report)
        
        # Save report to file
        output_file = Path(__file__).resolve().parents[1] / "reports" / "psa_analysis.md"
        analyzer.generate_psa_report(iterations=1000, output_file=str(output_file))
        print(f"Report saved to {output_file}")
        
    except Exception as e:
        print(f"Error in PSA analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()