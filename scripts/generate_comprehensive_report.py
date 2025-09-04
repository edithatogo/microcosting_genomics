#!/usr/bin/env python3
"""
Script to generate a comprehensive report integrating all microcosting analyses.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.comprehensive_reporting import ComprehensiveReporter
from unimelb_phd_phase_1.data_manager import DataManager


def main():
    """Main function to generate comprehensive report."""
    print("Generating comprehensive microcosting analysis report...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize reporter
        reporter = ComprehensiveReporter(data_manager)
        
        # Generate integrated report
        report = reporter.generate_integrated_report()
        print(report)
        
        # Save report to file
        output_dir = Path(__file__).resolve().parents[1] / "reports" / "comprehensive_analysis"
        report_output = reporter.generate_integrated_report(output_dir=str(output_dir))
        print(f"Comprehensive report saved to {output_dir}")
        
    except Exception as e:
        print(f"Error in comprehensive reporting: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()