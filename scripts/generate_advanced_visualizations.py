#!/usr/bin/env python3
"""
Script to generate advanced visualizations with interactive features.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.visualization import load_prepared_data  # noqa: E402
from genomics_microcosting.advanced_visualization import create_comprehensive_visualization_report  # noqa: E402


def main():
    """Main function to generate advanced visualizations."""
    print("Generating advanced visualizations...")
    
    try:
        # Load data
        data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
        output_dir = Path(__file__).resolve().parents[1] / "reports" / "advanced_visualizations"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        print(f"Loading data from {data_dir}")
        data_dict = load_prepared_data(data_dir)
        print(f"Loaded {len(data_dict)} data tables")
        
        if not data_dict:
            print("Error: No data loaded. Cannot generate visualizations.")
            return 1
        
        # Generate comprehensive visualization report
        print(f"Creating advanced visualizations in {output_dir}")
        figures = create_comprehensive_visualization_report(data_dict, output_dir)
        print(f"Created {len(figures)} advanced visualizations")
        
        # List generated files
        print("\nGenerated files:")
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                print(f"  - {file_path.name}")
        
        print("\nAdvanced visualization generation complete!")
        print(f"Visualizations saved to {output_dir}")
        
    except Exception as e:
        print(f"Error generating advanced visualizations: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())