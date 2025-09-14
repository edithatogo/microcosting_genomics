#!/usr/bin/env python3
"""
Script to analyze cost drivers in the microcosting model.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer  # noqa: E402
from genomics_microcosting.data_manager import DataManager  # noqa: E402


def main():
    """Main function to run cost driver analysis."""
    print("Running cost driver analysis...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = CostDriverAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_cost_driver_report()
        print(report)
        
        # Save report to file
        output_file = Path(__file__).resolve().parents[1] / "reports" / "cost_driver_analysis.md"
        analyzer.generate_cost_driver_report(str(output_file))
        print(f"Report saved to {output_file}")
        
    except Exception as e:
        print(f"Error in cost driver analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()