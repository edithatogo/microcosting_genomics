#!/usr/bin/env python3
"""
Script to perform Value of Information (VOI) Analysis on the microcosting model.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.voi_analysis import VOIAnalyzer
from unimelb_phd_phase_1.data_manager import DataManager


def main():
    """Main function to run VOI analysis."""
    print("Running Value of Information (VOI) Analysis...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = VOIAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_voi_report(iterations=1000)
        print(report)
        
        # Save report to file
        output_file = Path(__file__).resolve().parents[1] / "reports" / "voi_analysis.md"
        analyzer.generate_voi_report(iterations=1000, output_file=str(output_file))
        print(f"Report saved to {output_file}")
        
    except Exception as e:
        print(f"Error in VOI analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()