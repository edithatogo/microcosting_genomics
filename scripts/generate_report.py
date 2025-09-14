#!/usr/bin/env python3
"""
Script to generate automated reports with visualizations and summary statistics.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.visualization import create_summary_dashboard, load_prepared_data  # noqa: E402


def generate_summary_statistics(data_dict, output_file):
    """Generate summary statistics for all data tables.
    
    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys
        output_file (str or Path): Path to output file
    """
    with open(output_file, "w") as f:
        f.write("# Microcosting Analysis Report\n\n")
        f.write("## Summary Statistics\n\n")
        
        for table_name, df in data_dict.items():
            f.write(f"### {table_name}\n\n")
            f.write(f"- Number of rows: {len(df)}\n")
            f.write(f"- Number of columns: {len(df.columns)}\n\n")
            
            # Numeric column statistics
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                f.write("#### Numeric Columns Summary\n\n")
                f.write(df[numeric_cols].describe().to_markdown() + "\n\n")
            
            # Categorical column information
            categorical_cols = df.select_dtypes(include=["object"]).columns
            if len(categorical_cols) > 0:
                f.write("#### Categorical Columns\n\n")
                for col in categorical_cols[:5]:  # Limit to first 5
                    unique_count = df[col].nunique()
                    f.write(f"- **{col}**: {unique_count} unique values\n")
                if len(categorical_cols) > 5:
                    f.write(f"- *... and {len(categorical_cols) - 5} more categorical columns*\n")
                f.write("\n")
            
            f.write("---\n\n")


def main():
    """Main function to generate automated report."""
    print("Generating automated report...")
    
    try:
        # Load data
        data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
        output_dir = Path(__file__).resolve().parents[1] / "reports"
        output_dir.mkdir(exist_ok=True)
        
        print(f"Loading data from {data_dir}")
        data_dict = load_prepared_data(data_dir)
        print(f"Loaded {len(data_dict)} data tables")
        
        # Generate summary statistics
        stats_file = output_dir / "summary_statistics.md"
        print(f"Generating summary statistics in {stats_file}")
        generate_summary_statistics(data_dict, stats_file)
        
        # Generate visualizations
        viz_dir = output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        print(f"Generating visualizations in {viz_dir}")
        figures = create_summary_dashboard(data_dir, viz_dir)
        print(f"Created {len(figures)} visualizations")
        
        # Generate combined report
        report_file = output_dir / "microcosting_report.md"
        print(f"Generating combined report in {report_file}")
        
        with open(report_file, "w") as f:
            f.write("# Microcosting Analysis Report\n\n")
            f.write("## Executive Summary\n\n")
            f.write("This report provides an automated analysis of the microcosting data for rare disease genomics.\n\n")
            
            f.write("## Data Overview\n\n")
            for table_name, df in data_dict.items():
                f.write(f"- **{table_name}**: {len(df)} rows, {len(df.columns)} columns\n")
            f.write("\n")
            
            f.write("## Generated Visualizations\n\n")
            for fig_file in viz_dir.glob("*.png"):
                f.write(f"![{fig_file.stem}]({fig_file.name})\n\n")
            
            f.write("## Detailed Statistics\n\n")
            f.write("See [summary_statistics.md](summary_statistics.md) for detailed statistics.\n\n")
        
        print("Report generation complete!")
        print(f"Reports saved to {output_dir}")
        
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())

