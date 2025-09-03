#!/usr/bin/env python3
"""
Script to create visualizations of cost data.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.visualization import create_summary_dashboard


def main():
    """Main function to create visualizations."""
    print("Creating cost visualization dashboard...")
    
    try:
        # Create dashboard
        figures = create_summary_dashboard()
        print(f"Created {len(figures)} visualizations")
        print("Dashboard creation complete!")
        
    except Exception as e:
        print(f"Error creating visualizations: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())