#!/usr/bin/env python3
"""
Script to perform Break-even Analysis on the microcosting model.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.break_even_analysis import BreakEvenAnalyzer
from unimelb_phd_phase_1.data_manager import DataManager


def main():
    """Main function to run break-even analysis."""
    print("Running Break-even Analysis...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize analyzer
        analyzer = BreakEvenAnalyzer(data_manager)
        
        # Generate report
        report = analyzer.generate_break_even_report()
        print(report)
        
        # Save report to file
        output_file = Path(__file__).resolve().parents[1] / "reports" / "break_even_analysis.md"
        analyzer.generate_break_even_report(output_file=str(output_file))
        print(f"Report saved to {output_file}")
        
    except Exception as e:
        print(f"Error in break-even analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()