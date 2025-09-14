#!/usr/bin/env python3
"""
Enhanced reporting script with support for multiple output formats including PDF and HTML.
"""

import sys
from pathlib import Path
import json
from datetime import datetime
import matplotlib.pyplot as plt

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("Warning: weasyprint not available. PDF generation will be disabled.")

try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("Warning: jinja2 not available. HTML template generation will be limited.")

from genomics_microcosting.visualization import (  # noqa: E402
    load_prepared_data, 
    plot_cost_distribution,
    plot_category_costs,
    plot_top_costs
)


def generate_markdown_report(data_dict, output_file, figures_dir=None):
    """Generate a comprehensive markdown report.
    
    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys
        output_file (str or Path): Path to output markdown file
        figures_dir (str or Path, optional): Directory containing figures
    """
    with open(output_file, "w") as f:
        f.write("# Microcosting Analysis Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write("This comprehensive report provides an automated analysis of the microcosting data for rare disease genomics. ")
        f.write("The analysis includes data overview, visualizations, and detailed statistics.\n\n")
        
        f.write("## Data Overview\n\n")
        total_rows = 0
        for table_name, df in data_dict.items():
            f.write(f"- **{table_name}**: {len(df)} rows, {len(df.columns)} columns\n")
            total_rows += len(df)
        f.write(f"\n**Total rows across all tables: {total_rows}**\n\n")
        
        f.write("## Generated Visualizations\n\n")
        if figures_dir and Path(figures_dir).exists():
            for fig_file in Path(figures_dir).glob("*.png"):
                f.write(f"![{fig_file.stem}]({fig_file.name})\n\n")
        else:
            f.write("No visualizations available.\n\n")
        
        f.write("## Detailed Statistics\n\n")
        for table_name, df in data_dict.items():
            f.write(f"### {table_name}\n\n")
            f.write(f"- Number of rows: {len(df)}\n")
            f.write(f"- Number of columns: {len(df.columns)}\n\n")
            
            # Numeric column statistics
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                f.write("#### Numeric Columns Summary\n\n")
                # Limit to first 10 numeric columns to avoid overly long reports
                cols_to_describe = numeric_cols[:10]
                desc_df = df[cols_to_describe].describe()
                # Convert to markdown format
                f.write(desc_df.to_markdown() + "\n\n")
                if len(numeric_cols) > 10:
                    f.write(f"*Note: Only first 10 of {len(numeric_cols)} numeric columns shown*\n\n")
            
            # Categorical column information
            categorical_cols = df.select_dtypes(include=["object"]).columns
            if len(categorical_cols) > 0:
                f.write("#### Categorical Columns\n\n")
                for col in categorical_cols[:10]:  # Limit to first 10
                    unique_count = df[col].nunique()
                    f.write(f"- **{col}**: {unique_count} unique values\n")
                if len(categorical_cols) > 10:
                    f.write(f"- *... and {len(categorical_cols) - 10} more categorical columns*\n")
                f.write("\n")
            
            f.write("---\n\n")


def generate_html_report(data_dict, output_file, figures_dir=None, template_file=None):
    """Generate an HTML report.
    
    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys
        output_file (str or Path): Path to output HTML file
        figures_dir (str or Path, optional): Directory containing figures
        template_file (str or Path, optional): Custom Jinja2 template file
    """
    if not JINJA2_AVAILABLE:
        # Fallback to simple HTML generation
        with open(output_file, "w") as f:
            f.write("<!DOCTYPE html>\n<html>\n<head>\n")
            f.write("<title>Microcosting Analysis Report</title>\n")
            f.write("<style>body { font-family: Arial, sans-serif; }</style>\n")
            f.write("</head>\n<body>\n")
            f.write("<h1>Microcosting Analysis Report</h1>\n")
            f.write(f"<p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
            
            f.write("<h2>Executive Summary</h2>\n")
            f.write("<p>This comprehensive report provides an automated analysis of the microcosting data for rare disease genomics.</p>\n")
            
            f.write("<h2>Data Overview</h2>\n<ul>\n")
            for table_name, df in data_dict.items():
                f.write(f"<li><strong>{table_name}</strong>: {len(df)} rows, {len(df.columns)} columns</li>\n")
            f.write("</ul>\n")
            
            f.write("<h2>Visualizations</h2>\n")
            if figures_dir and Path(figures_dir).exists():
                f.write("<div>\n")
                for fig_file in Path(figures_dir).glob("*.png"):
                    f.write(f'<img src="{fig_file.name}" alt="{fig_file.stem}" style="max-width: 100%; height: auto;">\n')
                f.write("</div>\n")
            else:
                f.write("<p>No visualizations available.</p>\n")
            
            f.write("</body>\n</html>\n")
        return
    
    # Use Jinja2 template if available
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(Path(__file__).parent)))
    
    # Default template
    template_str = """
<!DOCTYPE html>
<html>
<head>
    <title>Microcosting Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1, h2, h3 { color: #2c3e50; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        img { max-width: 100%; height: auto; margin: 20px 0; }
        .summary-stats { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Microcosting Analysis Report</h1>
    <p>Generated on: {{ generated_date }}</p>
    
    <h2>Executive Summary</h2>
    <p>This comprehensive report provides an automated analysis of the microcosting data for rare disease genomics. 
    The analysis includes data overview, visualizations, and detailed statistics.</p>
    
    <h2>Data Overview</h2>
    <div class="summary-stats">
        <p><strong>Total tables:</strong> {{ data_dict|length }}</p>
        <p><strong>Total rows across all tables:</strong> {{ total_rows }}</p>
    </div>
    
    <ul>
    {% for table_name, df in data_dict.items() %}
        <li><strong>{{ table_name }}</strong>: {{ df.shape[0] }} rows, {{ df.shape[1] }} columns</li>
    {% endfor %}
    </ul>
    
    <h2>Visualizations</h2>
    {% if figures %}
        <div>
        {% for figure in figures %}
            <img src="{{ figure }}" alt="{{ figure }}">
        {% endfor %}
        </div>
    {% else %}
        <p>No visualizations available.</p>
    {% endif %}
    
    <h2>Detailed Statistics</h2>
    {% for table_name, df in data_dict.items() %}
        <h3>{{ table_name }}</h3>
        <p><strong>Rows:</strong> {{ df.shape[0] }} | <strong>Columns:</strong> {{ df.shape[1] }}</p>
        
        {% if numeric_cols[table_name] %}
            <h4>Numeric Columns Summary</h4>
            <p>Showing first 10 of {{ numeric_cols[table_name]|length }} numeric columns:</p>
            {{ df[numeric_cols[table_name][:10]].describe().to_html()|safe }}
        {% endif %}
        
        {% if categorical_cols[table_name] %}
            <h4>Categorical Columns</h4>
            <p>Showing first 10 of {{ categorical_cols[table_name]|length }} categorical columns:</p>
            <ul>
            {% for col in categorical_cols[table_name][:10] %}
                <li><strong>{{ col }}</strong>: {{ df[col].nunique() }} unique values</li>
            {% endfor %}
            </ul>
        {% endif %}
    {% endfor %}
</body>
</html>
    """
    
    if template_file and Path(template_file).exists():
        template = env.get_template(Path(template_file).name)
    else:
        template = jinja2.Template(template_str)
    
    # Prepare data for template
    numeric_cols = {}
    categorical_cols = {}
    total_rows = 0
    
    for table_name, df in data_dict.items():
        numeric_cols[table_name] = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols[table_name] = df.select_dtypes(include=["object"]).columns.tolist()
        total_rows += len(df)
    
    figures = []
    if figures_dir and Path(figures_dir).exists():
        figures = [str(fig_file.name) for fig_file in Path(figures_dir).glob("*.png")]
    
    html_content = template.render(
        generated_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        data_dict=data_dict,
        numeric_cols=numeric_cols,
        categorical_cols=categorical_cols,
        total_rows=total_rows,
        figures=figures
    )
    
    with open(output_file, "w") as f:
        f.write(html_content)


def generate_pdf_report(html_file, output_file):
    """Generate a PDF report from HTML.
    
    Args:
        html_file (str or Path): Path to input HTML file
        output_file (str or Path): Path to output PDF file
    """
    if not WEASYPRINT_AVAILABLE:
        print("Error: weasyprint is not available. Cannot generate PDF report.")
        print("Install it with: pip install weasyprint")
        return False
    
    try:
        HTML(str(html_file)).write_pdf(str(output_file))
        return True
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return False


def create_cost_analysis_plots(data_dict, output_dir):
    """Create detailed cost analysis plots.
    
    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys
        output_dir (str or Path): Directory to save plots
        
    Returns:
        list: List of generated figure filenames
    """
    figures = []
    
    if 'detailed_table' not in data_dict:
        print("Warning: detailed_table not found in data. Skipping detailed plots.")
        return figures
    
    detailed_data = data_dict['detailed_table']
    
    # Find cost columns
    cost_columns = [col for col in detailed_data.columns if 'Unit Cost' in col or 'Price' in col]
    category_columns = [col for col in detailed_data.columns if 'Category' in col]
    
    if not cost_columns:
        # Try to find any numeric columns
        numeric_columns = detailed_data.select_dtypes(include=['number']).columns.tolist()
        if numeric_columns:
            cost_columns = [numeric_columns[0]]
    
    # Create plots
    try:
        # Cost distribution plot
        if cost_columns:
            fig = plot_cost_distribution(detailed_data, cost_columns[0], 
                                       f"Distribution of {cost_columns[0]}")
            fig_file = Path(output_dir) / f"cost_distribution_{cost_columns[0].replace('/', '_')}.png"
            fig.savefig(fig_file, bbox_inches='tight', dpi=300)
            plt.close(fig)
            figures.append(str(fig_file.name))
        
        # Category costs plot
        if category_columns and cost_columns:
            fig = plot_category_costs(detailed_data, category_columns[0], cost_columns[0],
                                    f"Total {cost_columns[0]} by {category_columns[0]}")
            fig_file = Path(output_dir) / f"costs_by_{category_columns[0].replace('/', '_')}.png"
            fig.savefig(fig_file, bbox_inches='tight', dpi=300)
            plt.close(fig)
            figures.append(str(fig_file.name))
        
        # Top costs plot
        if cost_columns:
            fig = plot_top_costs(detailed_data, cost_columns[0], top_n=20,
                               title=f"Top 20 {cost_columns[0]}")
            fig_file = Path(output_dir) / f"top_20_{cost_columns[0].replace('/', '_')}.png"
            fig.savefig(fig_file, bbox_inches='tight', dpi=300)
            plt.close(fig)
            figures.append(str(fig_file.name))
            
    except Exception as e:
        print(f"Warning: Error creating detailed plots: {e}")
    
    return figures


def generate_json_report(data_dict, output_file):
    """Generate a JSON report with summary statistics.
    
    Args:
        data_dict (dict): Dictionary of DataFrames with table names as keys
        output_file (str or Path): Path to output JSON file
    """
    report_data = {
        "generated_date": datetime.now().isoformat(),
        "tables": {},
        "summary": {
            "total_tables": len(data_dict),
            "total_rows": sum(len(df) for df in data_dict.values())
        }
    }
    
    for table_name, df in data_dict.items():
        table_info = {
            "rows": len(df),
            "columns": len(df.columns),
            "numeric_columns": len(df.select_dtypes(include=["number"]).columns),
            "categorical_columns": len(df.select_dtypes(include=["object"]).columns),
            "missing_values": int(df.isnull().sum().sum()),
            "column_names": df.columns.tolist()
        }
        
        # Add summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            desc = df[numeric_cols].describe()
            table_info["numeric_summary"] = {}
            for col in numeric_cols[:10]:  # Limit to first 10
                table_info["numeric_summary"][col] = desc[col].to_dict()
        
        report_data["tables"][table_name] = table_info
    
    with open(output_file, "w") as f:
        json.dump(report_data, f, indent=2)


def main():
    """Main function to generate enhanced reports in multiple formats."""
    print("Generating enhanced reports...")
    
    try:
        # Load data
        data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
        output_dir = Path(__file__).resolve().parents[1] / "reports"
        output_dir.mkdir(exist_ok=True)
        
        print(f"Loading data from {data_dir}")
        data_dict = load_prepared_data(data_dir)
        print(f"Loaded {len(data_dict)} data tables")
        
        if not data_dict:
            print("Error: No data loaded. Cannot generate reports.")
            return 1
        
        # Create visualizations directory
        viz_dir = output_dir / "enhanced_visualizations"
        viz_dir.mkdir(exist_ok=True)
        print(f"Creating enhanced visualizations in {viz_dir}")
        figures = create_cost_analysis_plots(data_dict, viz_dir)
        print(f"Created {len(figures)} enhanced visualizations")
        
        # Generate markdown report
        md_file = output_dir / "enhanced_microcosting_report.md"
        print(f"Generating markdown report in {md_file}")
        generate_markdown_report(data_dict, md_file, viz_dir)
        
        # Generate HTML report
        html_file = output_dir / "enhanced_microcosting_report.html"
        print(f"Generating HTML report in {html_file}")
        generate_html_report(data_dict, html_file, viz_dir)
        
        # Generate PDF report (if weasyprint is available)
        if WEASYPRINT_AVAILABLE:
            pdf_file = output_dir / "enhanced_microcosting_report.pdf"
            print(f"Generating PDF report in {pdf_file}")
            if generate_pdf_report(html_file, pdf_file):
                print("PDF report generated successfully")
            else:
                print("Failed to generate PDF report")
        else:
            print("Skipping PDF report (weasyprint not available)")
        
        # Generate JSON report
        json_file = output_dir / "enhanced_microcosting_report.json"
        print(f"Generating JSON report in {json_file}")
        generate_json_report(data_dict, json_file)
        
        print("Enhanced report generation complete!")
        print(f"Reports saved to {output_dir}")
        
        # List generated files
        print("\nGenerated files:")
        for file_path in output_dir.iterdir():
            if file_path.is_file() and "enhanced" in file_path.name:
                print(f"  - {file_path.name}")
        
        for file_path in viz_dir.iterdir():
            if file_path.is_file():
                print(f"  - enhanced_visualizations/{file_path.name}")
        
    except Exception as e:
        print(f"Error generating enhanced reports: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())