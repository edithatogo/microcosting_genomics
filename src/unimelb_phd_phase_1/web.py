"""Web interface for microcosting analysis."""

from flask import Flask, render_template, request, jsonify
import pandas as pd
from pathlib import Path
import sys

# Add the src directory to the path
src_path = Path(__file__).resolve().parent
sys.path.insert(0, str(src_path))

from .visualization import load_prepared_data, plot_cost_distribution, plot_category_costs
from .web_viz import generate_visualization, get_available_columns


def create_app(data_dir=None):
    """Create and configure the Flask application.
    
    Args:
        data_dir (str or Path, optional): Path to the data directory.
        
    Returns:
        Flask: Configured Flask application.
    """
    app = Flask(__name__, 
                template_folder=Path(__file__).resolve().parent / "templates",
                static_folder=Path(__file__).resolve().parent / "static")
    
    # Load data when app is created
    try:
        app.data = load_prepared_data(data_dir)
        app.logger.info(f"Loaded {len(app.data)} data tables")
    except Exception as e:
        app.logger.error(f"Error loading data: {e}")
        app.data = {}
    
    @app.route("/")
    def index():
        """Main page showing available data tables."""
        tables = list(app.data.keys()) if app.data else []
        return render_template("index.html", tables=tables)
    
    @app.route("/table/<table_name>")
    def show_table(table_name):
        """Show a specific data table."""
        if table_name not in app.data:
            return f"Table \"{table_name}\" not found", 404
            
        df = app.data[table_name]
        # Get first 100 rows and first 10 columns for display
        display_df = df.iloc[:100, :10] if len(df) > 0 else df
        columns = display_df.columns.tolist()
        data = display_df.to_dict("records")
        
        return render_template("table.html", 
                             table_name=table_name,
                             columns=columns, 
                             data=data)
    
    @app.route("/api/tables")
    def api_tables():
        """API endpoint to get list of available tables."""
        return jsonify(list(app.data.keys()))
    
    @app.route("/api/table/<table_name>")
    def api_table_data(table_name):
        """API endpoint to get table data."""
        if table_name not in app.data:
            return jsonify({"error": f"Table {table_name} not found"}), 404
            
        df = app.data[table_name]
        # Return first 50 rows for API
        result_df = df.head(50) if len(df) > 0 else df
        return jsonify({
            "columns": result_df.columns.tolist(),
            "data": result_df.to_dict("records")
        })
    
    @app.route("/visualize")
    def visualize():
        """Page for visualizations."""
        tables = list(app.data.keys()) if app.data else []
        return render_template("visualize.html", tables=tables)
    
    @app.route('/visualize/table/<table_name>')
    def visualize_table(table_name):
        """Generate visualization for a specific table."""
        if table_name not in app.data:
            return f"Table '{table_name}' not found", 404
            
        # For now, just return to the main visualize page
        # In future, we can add specific visualization logic here
        tables = list(app.data.keys()) if app.data else []
        return render_template('visualize.html', tables=tables, selected_table=table_name)
    
    @app.route('/api/visualize/<table_name>')
    def api_visualize(table_name):
        """API endpoint to generate visualization data for a table."""
        if table_name not in app.data:
            return jsonify({'error': f'Table {table_name} not found'}), 404
            
        df = app.data[table_name]
        
        # Find numeric columns for visualization
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        category_columns = [col for col in df.columns if 'Category' in col or 'category' in col.lower()]
        
        return jsonify({
            'table_name': table_name,
            'numeric_columns': numeric_columns[:10],  # Limit to first 10
            'category_columns': category_columns[:5],  # Limit to first 5
            'row_count': len(df),
            'column_count': len(df.columns)
        })
    
    @app.route('/api/generate_viz/<table_name>')
    def api_generate_viz(table_name):
        """API endpoint to generate a visualization for a table."""
        if table_name not in app.data:
            return jsonify({'error': f'Table {table_name} not found'}), 404
            
        df = app.data[table_name]
        
        # Get parameters from request
        viz_type = request.args.get('type', 'distribution')
        column_name = request.args.get('column')
        category_column = request.args.get('category')
        
        try:
            # Generate the visualization
            img_base64 = generate_visualization(df, viz_type, column_name, category_column)
            
            return jsonify({
                'success': True,
                'image': img_base64,
                'table_name': table_name,
                'viz_type': viz_type
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/table_info/<table_name>')
    def api_table_info(table_name):
        """API endpoint to get information about a table."""
        if table_name not in app.data:
            return jsonify({'error': f'Table {table_name} not found'}), 404
            
        df = app.data[table_name]
        
        # Get column information
        columns_info = []
        for col in df.columns:
            columns_info.append({
                'name': col,
                'dtype': str(df[col].dtype),
                'null_count': int(df[col].isnull().sum()),
                'unique_count': int(df[col].nunique()) if df[col].dtype == 'object' else None
            })
        
        return jsonify({
            'table_name': table_name,
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': columns_info,
            'available_columns': get_available_columns(df)
        })
    
    return app


def main():
    """Main function to run the web application."""
    app = create_app()
    
    # Run the app
    app.run(debug=True, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()