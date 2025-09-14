"""Web interface for microcosting analysis."""

from flask import Flask, render_template, request, jsonify, Response
from pathlib import Path
import sys
import io
import pandas as pd

# Add the src directory to the path
src_path = Path(__file__).resolve().parent
sys.path.insert(0, str(src_path))

from .visualization import load_prepared_data  # noqa: E402
from .web_viz import generate_visualization, get_available_columns  # noqa: E402


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
    
    # Set up monitoring components
    try:
        from .monitoring import setup_standard_monitoring
        app.health_checker, app.metrics_collector, app.usage_analytics, app.alert_manager, app.monitoring_middleware = setup_standard_monitoring(app.logger)
        app.logger.info("Monitoring components initialized")
    except Exception as e:
        app.logger.error(f"Error setting up monitoring: {e}")
        app.health_checker = None
    
    @app.route("/")
    def index():
        """Main page showing available data tables."""
        tables = list(app.data.keys()) if app.data else []
        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "view_home", "home_page")
        return render_template("index.html", tables=tables)
    
    @app.route("/table/<table_name>")
    def show_table(table_name):
        """Show a specific data table."""
        if table_name not in app.data:
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "view_table_not_found", table_name)
            return f"Table \"{table_name}\" not found", 404
            
        df = app.data[table_name]
        # Get first 100 rows and first 10 columns for display
        display_df = df.iloc[:100, :10] if len(df) > 0 else df
        columns = display_df.columns.tolist()
        data = display_df.to_dict("records")
        
        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "view_table", table_name, {"rows": len(df), "columns": len(df.columns)})
        
        return render_template("table.html", 
                             table_name=table_name,
                             columns=columns, 
                             data=data)
    
    @app.route("/api/tables")
    def api_tables():
        """API endpoint to get list of available tables."""
        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "api_get_tables", "api")
        return jsonify(list(app.data.keys()))
    
    @app.route("/api/table/<table_name>")
    def api_table_data(table_name):
        """API endpoint to get table data."""
        if table_name not in app.data:
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "api_get_table_not_found", table_name)
            return jsonify({"error": f"Table {table_name} not found"}), 404
            
        df = app.data[table_name]
        # Return first 50 rows for API
        result_df = df.head(50) if len(df) > 0 else df
        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "api_get_table", table_name, {"rows": len(result_df)})
        return jsonify({
            "columns": result_df.columns.tolist(),
            "data": result_df.to_dict("records")
        })
    
    @app.route("/visualize")
    def visualize():
        """Page for visualizations."""
        tables = list(app.data.keys()) if app.data else []
        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "view_visualize", "visualize_page")
        return render_template("visualize.html", tables=tables)
    
    @app.route('/visualize/table/<table_name>')
    def visualize_table(table_name):
        """Generate visualization for a specific table."""
        if table_name not in app.data:
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "view_visualize_table_not_found", table_name)
            return f"Table '{table_name}' not found", 404
            
        # For now, just return to the main visualize page
        # In future, we can add specific visualization logic here
        tables = list(app.data.keys()) if app.data else []
        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "view_visualize_table", table_name)
        return render_template('visualize.html', tables=tables, selected_table=table_name)
    
    @app.route('/api/visualize/<table_name>')
    def api_visualize(table_name):
        """API endpoint to generate visualization data for a table."""
        if table_name not in app.data:
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "api_visualize_not_found", table_name)
            return jsonify({'error': f'Table {table_name} not found'}), 404
            
        df = app.data[table_name]
        
        # Find numeric columns for visualization
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        category_columns = [col for col in df.columns if 'Category' in col or 'category' in col.lower()]
        
        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "api_get_visualize_data", table_name)
        
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
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "api_generate_viz_not_found", table_name)
            return jsonify({'error': f'Table {table_name} not found'}), 404
            
        df = app.data[table_name]
        
        # Get parameters from request
        viz_type = request.args.get('type', 'distribution')
        column_name = request.args.get('column')
        category_column = request.args.get('category')
        
        try:
            # Generate the visualization
            img_base64 = generate_visualization(df, viz_type, column_name, category_column)
            
            # Log this user action
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "api_generate_visualization", table_name, {
                    "viz_type": viz_type,
                    "column": column_name,
                    "category_column": category_column
                })
            
            return jsonify({
                'success': True,
                'image': img_base64,
                'table_name': table_name,
                'viz_type': viz_type
            })
        except Exception as e:
            # Log this error
            if app.alert_manager:
                app.alert_manager.send_alert("visualization_error", f"Error generating visualization for {table_name}: {str(e)}", "error")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/table_info/<table_name>')
    def api_table_info(table_name):
        """API endpoint to get information about a table."""
        if table_name not in app.data:
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "api_table_info_not_found", table_name)
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
        
        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "api_get_table_info", table_name)
        
        return jsonify({
            'table_name': table_name,
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': columns_info,
            'available_columns': get_available_columns(df)
        })
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        if not app.health_checker:
            return jsonify({"status": "unhealthy", "error": "Health checker not initialized"}), 500
        
        try:
            health_results = app.health_checker.run_health_check()
            status_code = 200 if health_results["status"] == "healthy" else 503
            return jsonify(health_results), status_code
        except Exception as e:
            if app.alert_manager:
                app.alert_manager.send_alert("health_check_error", f"Health check failed: {str(e)}", "error")
            return jsonify({"status": "unhealthy", "error": str(e)}), 500
    
    @app.route('/metrics')
    def metrics():
        """Performance metrics endpoint."""
        if not app.metrics_collector:
            return jsonify({"error": "Metrics collector not initialized"}), 500
        
        try:
            metrics_summary = app.metrics_collector.get_metrics_summary()
            return jsonify(metrics_summary)
        except Exception as e:
            if app.alert_manager:
                app.alert_manager.send_alert("metrics_error", f"Metrics collection failed: {str(e)}", "error")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/alerts')
    def alerts():
        """Recent alerts endpoint."""
        if not app.alert_manager:
            return jsonify({"error": "Alert manager not initialized"}), 500
        
        try:
            recent_alerts = app.alert_manager.get_recent_alerts()
            return jsonify(recent_alerts)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/dashboard')
    def dashboard():
        """Interactive dashboard with comprehensive data overview."""
        if not app.data:
            return render_template("dashboard.html",
                                 tables=[],
                                 total_rows=0,
                                 total_columns=0,
                                 visualizations_count=0,
                                 table_info={})

        # Calculate summary statistics
        total_rows = sum(len(df) for df in app.data.values())
        total_columns = sum(len(df.columns) for df in app.data.values())

        # Create table information
        table_info = {}
        for name, df in app.data.items():
            # Generate descriptions based on table names
            descriptions = {
                'detailed_table': 'Primary cost calculation table with all process steps',
                'dsa__labour_prices': 'Labor cost rates for sensitivity analysis',
                'dsa__test_throughput': 'Test volume assumptions for DSA',
                'summary_table': 'High-level cost summaries by test type',
                'at_a_glance': 'Executive summary of key cost metrics'
            }

            table_info[name] = {
                'rows': len(df),
                'columns': len(df.columns),
                'description': descriptions.get(name, f'Data table: {name}')
            }

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "view_dashboard", "dashboard_page")

        return render_template("dashboard.html",
                             tables=list(app.data.keys()),
                             total_rows=total_rows,
                             total_columns=total_columns,
                             visualizations_count=3,  # Number of chart types available
                             table_info=table_info)

    @app.route('/api/dashboard/cost-distribution')
    def api_dashboard_cost_distribution():
        """API endpoint for cost distribution chart."""
        if not app.data or 'detailed_table' not in app.data:
            return jsonify({'error': 'Detailed table not found'}), 404

        df = app.data['detailed_table']

        # Find cost columns
        cost_columns = [col for col in df.columns if 'cost' in col.lower() or 'price' in col.lower()]
        if not cost_columns:
            return jsonify({'error': 'No cost columns found'}), 404

        try:
            # Generate cost distribution visualization
            img_base64 = generate_visualization(df, 'distribution', cost_columns[0])

            # Log this user action
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "api_dashboard_cost_dist", "dashboard")

            return jsonify({'success': True, 'image': img_base64})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/dashboard/top-categories')
    def api_dashboard_top_categories():
        """API endpoint for top categories chart."""
        if not app.data or 'detailed_table' not in app.data:
            return jsonify({'error': 'Detailed table not found'}), 404

        df = app.data['detailed_table']

        # Find category and cost columns
        category_columns = [col for col in df.columns if 'category' in col.lower()]
        cost_columns = [col for col in df.columns if 'cost' in col.lower() or 'price' in col.lower()]

        if not category_columns or not cost_columns:
            return jsonify({'error': 'Required columns not found'}), 404

        try:
            # Generate top categories visualization
            img_base64 = generate_visualization(df, 'category', cost_columns[0], category_columns[0])

            # Log this user action
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "api_dashboard_top_cat", "dashboard")

            return jsonify({'success': True, 'image': img_base64})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/export/all/zip')
    def export_all_zip():
        """Export all tables as a ZIP file."""
        if not app.data:
            return jsonify({'error': 'No data available'}), 404

        try:
            import zipfile
            from io import BytesIO

            # Create ZIP file in memory
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for table_name, df in app.data.items():
                    # Add CSV file
                    csv_content = df.to_csv(index=False)
                    zip_file.writestr(f'{table_name}.csv', csv_content)

                    # Add JSON file
                    json_content = df.to_json(orient='records', indent=2)
                    zip_file.writestr(f'{table_name}.json', json_content)

            zip_buffer.seek(0)

            # Log this user action
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "export_all_zip", "dashboard")

            return Response(
                zip_buffer.getvalue(),
                mimetype='application/zip',
                headers={'Content-Disposition': 'attachment; filename=microcosting_data.zip'}
            )
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/generate-report')
    def generate_report():
        """Generate a comprehensive PDF report."""
        if not app.data:
            return jsonify({'error': 'No data available'}), 404

        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from io import BytesIO

            # Create PDF in memory
            pdf_buffer = BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=letter)

            # Add title
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, 750, "Microcosting Analysis Report")

            # Add summary statistics
            c.setFont("Helvetica", 12)
            y_position = 700

            total_tables = len(app.data)
            total_rows = sum(len(df) for df in app.data.values())
            total_columns = sum(len(df.columns) for df in app.data.values())

            c.drawString(100, y_position, f"Total Tables: {total_tables}")
            y_position -= 20
            c.drawString(100, y_position, f"Total Records: {total_rows:,}")
            y_position -= 20
            c.drawString(100, y_position, f"Total Columns: {total_columns}")

            # Add table list
            y_position -= 40
            c.setFont("Helvetica-Bold", 14)
            c.drawString(100, y_position, "Available Tables:")
            y_position -= 20

            c.setFont("Helvetica", 10)
            for table_name, df in app.data.items():
                c.drawString(120, y_position, f"• {table_name}: {len(df)} rows, {len(df.columns)} columns")
                y_position -= 15
                if y_position < 100:  # Start new page if needed
                    c.showPage()
                    y_position = 750

            c.save()
            pdf_buffer.seek(0)

            # Log this user action
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "generate_report", "dashboard")

            return Response(
                pdf_buffer.getvalue(),
                mimetype='application/pdf',
                headers={'Content-Disposition': 'attachment; filename=microcosting_report.pdf'}
            )
        except ImportError:
            return jsonify({'error': 'PDF generation requires reportlab package'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/export/<table_name>/csv')
    def export_csv(table_name):
        """Export table data as CSV."""
        if table_name not in app.data:
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "export_csv_not_found", table_name)
            return jsonify({"error": f"Table {table_name} not found"}), 404

        df = app.data[table_name]

        # Create CSV content
        csv_content = df.to_csv(index=False)

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "export_csv", table_name, {"rows": len(df), "columns": len(df.columns)})

        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={table_name}.csv'}
        )

    @app.route('/api/export/<table_name>/excel')
    def export_excel(table_name):
        """Export table data as Excel file."""
        if table_name not in app.data:
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "export_excel_not_found", table_name)
            return jsonify({"error": f"Table {table_name} not found"}), 404

        df = app.data[table_name]

        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=table_name, index=False)

        output.seek(0)

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "export_excel", table_name, {"rows": len(df), "columns": len(df.columns)})

        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={table_name}.xlsx'}
        )

    @app.route('/api/export/<table_name>/json')
    def export_json(table_name):
        """Export table data as JSON."""
        if table_name not in app.data:
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "export_json_not_found", table_name)
            return jsonify({"error": f"Table {table_name} not found"}), 404

        df = app.data[table_name]

        # Convert to JSON
        json_data = df.to_json(orient='records', indent=2)

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "export_json", table_name, {"rows": len(df), "columns": len(df.columns)})

        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={table_name}.json'}
        )

    @app.route('/api/export/<table_name>/parquet')
    def export_parquet(table_name):
        """Export table data as Parquet file."""
        if table_name not in app.data:
            if app.usage_analytics:
                app.usage_analytics.log_user_action("anonymous", "export_parquet_not_found", table_name)
            return jsonify({"error": f"Table {table_name} not found"}), 404

        df = app.data[table_name]

        # Create Parquet file in memory
        output = io.BytesIO()
        df.to_parquet(output, index=False)
        output.seek(0)

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action("anonymous", "export_parquet", table_name, {"rows": len(df), "columns": len(df.columns)})

        return Response(
            output.getvalue(),
            mimetype='application/octet-stream',
            headers={'Content-Disposition': f'attachment; filename={table_name}.parquet'}
        )

    return app


def main():
    """Main function to run the web application."""
    app = create_app()
    
    # Run the app
    app.run(debug=True, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()