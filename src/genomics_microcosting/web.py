# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Web interface for microcosting analysis."""

import io
import zipfile
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from flask import Flask, Response, abort, jsonify, render_template, request
from openpyxl import Workbook
lazy from reportlab.lib.pagesizes import letter
lazy from reportlab.pdfgen import canvas

from .visualization import load_prepared_data
from .web_viz import generate_visualization, get_available_columns
lazy from . import monitoring

if TYPE_CHECKING:
    from .monitoring import (
        AlertManager,
        MonitoringMiddleware,
        PerformanceMetricsCollector,
        SystemHealthChecker,
        UsageAnalytics,
    )


_PDF_PAGE_BOTTOM = 100


class ResearchFlask(Flask):
    """The native table and optional monitoring state owned by this application."""

    data: dict[str, pl.DataFrame]
    health_checker: SystemHealthChecker | None
    metrics_collector: PerformanceMetricsCollector | None
    usage_analytics: UsageAnalytics | None
    alert_manager: AlertManager | None
    monitoring_middleware: MonitoringMiddleware | None


def create_app(data_dir: str | Path | None = None) -> ResearchFlask:
    """Create and configure the Flask application.

    Args:
        data_dir (str or Path, optional): Path to the data directory.

    Returns:
        Flask: Configured Flask application.

    """
    app = ResearchFlask(
        __name__,
        template_folder=Path(__file__).resolve().parent / "templates",
        static_folder=Path(__file__).resolve().parent / "static",
    )

    # Load data when app is created
    try:
        app.data = load_prepared_data(data_dir)
        app.logger.info("Loaded %s data tables", len(app.data))
    except Exception:
        app.logger.exception("Error loading data")
        app.data = {}

    # Set up monitoring components
    try:
        (
            app.health_checker,
            app.metrics_collector,
            app.usage_analytics,
            app.alert_manager,
            app.monitoring_middleware,
        ) = monitoring.setup_standard_monitoring(app.logger)
        app.logger.info("Monitoring components initialized")
    except Exception:
        app.logger.exception("Error setting up monitoring")
        app.health_checker = None
        app.metrics_collector = None
        app.usage_analytics = None
        app.alert_manager = None
        app.monitoring_middleware = None

    _register_table_routes(app)
    _register_visualization_routes(app)
    _register_monitoring_routes(app)
    _register_dashboard_routes(app)
    _register_export_routes(app)
    return app


def _register_table_routes(app: ResearchFlask) -> None:
    app.add_url_rule("/", "index", partial(_index, app))
    app.add_url_rule("/table/<table_name>", "show_table", partial(_show_table, app))
    app.add_url_rule("/api/tables", "api_tables", partial(_api_tables, app))
    app.add_url_rule(
        "/api/table/<table_name>",
        "api_table_data",
        partial(_api_table_data, app),
    )
    app.add_url_rule(
        "/api/table_info/<table_name>",
        "api_table_info",
        partial(_api_table_info, app),
    )


def _register_visualization_routes(app: ResearchFlask) -> None:
    app.add_url_rule("/visualize", "visualize", partial(_visualize, app))
    app.add_url_rule(
        "/visualize/table/<table_name>",
        "visualize_table",
        partial(_visualize_table, app),
    )
    app.add_url_rule(
        "/api/visualize/<table_name>",
        "api_visualize",
        partial(_api_visualize, app),
    )
    app.add_url_rule(
        "/api/generate_viz/<table_name>",
        "api_generate_viz",
        partial(_api_generate_viz, app),
    )


def _register_monitoring_routes(app: ResearchFlask) -> None:
    app.add_url_rule("/health", "health_check", partial(_health_check, app))
    app.add_url_rule("/metrics", "metrics", partial(_metrics, app))
    app.add_url_rule("/alerts", "alerts", partial(_alerts, app))


def _register_dashboard_routes(app: ResearchFlask) -> None:
    app.add_url_rule("/dashboard", "dashboard", partial(_dashboard, app))
    app.add_url_rule(
        "/api/dashboard/cost-distribution",
        "api_dashboard_cost_distribution",
        partial(_api_dashboard_cost_distribution, app),
    )
    app.add_url_rule(
        "/api/dashboard/top-categories",
        "api_dashboard_top_categories",
        partial(_api_dashboard_top_categories, app),
    )


def _register_export_routes(app: ResearchFlask) -> None:
    app.add_url_rule(
        "/api/export/all/zip",
        "export_all_zip",
        partial(_export_all_zip, app),
    )
    app.add_url_rule(
        "/api/generate-report",
        "generate_report",
        partial(_generate_report, app),
    )
    app.add_url_rule(
        "/api/export/<table_name>/csv",
        "export_csv",
        partial(_export_csv, app),
    )
    app.add_url_rule(
        "/api/export/<table_name>/excel",
        "export_excel",
        partial(_export_excel, app),
    )
    app.add_url_rule(
        "/api/export/<table_name>/json",
        "export_json",
        partial(_export_json, app),
    )
    app.add_url_rule(
        "/api/export/<table_name>/parquet",
        "export_parquet",
        partial(_export_parquet, app),
    )


def _index(app: ResearchFlask) -> Response | tuple[Response, int] | str:
    """Show available data tables."""
    tables = list(app.data.keys()) if app.data else []
    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action("anonymous", "view_home", "home_page")
    return render_template("index.html", tables=tables)


def _show_table(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Show a specific data table."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "view_table_not_found",
                table_name,
            )
        abort(404, description=f'Table "{table_name}" not found')

    df = app.data[table_name]
    # Get first 100 rows and first 10 columns for display
    display_df = df.head(100).select(df.columns[:10]) if len(df) > 0 else df
    columns = display_df.columns
    data = display_df.to_dicts()

    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "view_table",
            table_name,
            {"rows": len(df), "columns": len(df.columns)},
        )

    return render_template(
        "table.html",
        table_name=table_name,
        columns=columns,
        data=data,
    )


def _api_tables(app: ResearchFlask) -> Response | tuple[Response, int] | str:
    """List available tables."""
    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action("anonymous", "api_get_tables", "api")
    return jsonify(list(app.data.keys()))


def _api_table_data(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Return table data."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "api_get_table_not_found",
                table_name,
            )
        return jsonify({"error": f"Table {table_name} not found"}), 404

    df = app.data[table_name]
    # Return first 50 rows for API
    result_df = df.head(50) if len(df) > 0 else df
    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "api_get_table",
            table_name,
            {"rows": len(result_df)},
        )
    return jsonify(
        {
            "columns": result_df.columns,
            "data": result_df.to_dicts(),
        },
    )


def _visualize(app: ResearchFlask) -> Response | tuple[Response, int] | str:
    """Page for visualizations."""
    tables = list(app.data.keys()) if app.data else []
    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "view_visualize",
            "visualize_page",
        )
    return render_template("visualize.html", tables=tables)


def _visualize_table(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Generate visualization for a specific table."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "view_visualize_table_not_found",
                table_name,
            )
        abort(404, description=f"Table '{table_name}' not found")

    # For now, just return to the main visualize page
    # In future, we can add specific visualization logic here
    tables = list(app.data.keys()) if app.data else []
    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "view_visualize_table",
            table_name,
        )
    return render_template(
        "visualize.html",
        tables=tables,
        selected_table=table_name,
    )


def _api_visualize(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Generate visualization data for a table."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "api_visualize_not_found",
                table_name,
            )
        return jsonify({"error": f"Table {table_name} not found"}), 404

    df = app.data[table_name]

    # Find numeric columns for visualization
    numeric_columns = [name for name, dtype in df.schema.items() if dtype.is_numeric()]
    category_columns = [
        col for col in df.columns if "Category" in col or "category" in col.lower()
    ]

    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "api_get_visualize_data",
            table_name,
        )

    return jsonify(
        {
            "table_name": table_name,
            "numeric_columns": numeric_columns[:10],  # Limit to first 10
            "category_columns": category_columns[:5],  # Limit to first 5
            "row_count": len(df),
            "column_count": len(df.columns),
        },
    )


def _api_generate_viz(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Generate a visualization for a table."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "api_generate_viz_not_found",
                table_name,
            )
        return jsonify({"error": f"Table {table_name} not found"}), 404

    df = app.data[table_name]

    # Get parameters from request
    viz_type = request.args.get("type", "distribution")
    column_name = request.args.get("column")
    category_column = request.args.get("category")

    try:
        # Generate the visualization
        img_base64 = generate_visualization(
            df,
            viz_type,
            column_name,
            category_column,
        )

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "api_generate_visualization",
                table_name,
                {
                    "viz_type": viz_type,
                    "column": column_name,
                    "category_column": category_column,
                },
            )

        return jsonify(
            {
                "success": True,
                "image": img_base64,
                "table_name": table_name,
                "viz_type": viz_type,
            },
        )
    except Exception:
        app.logger.exception("Invalid visualization request")
        # Log this error
        if app.alert_manager:
            app.alert_manager.send_alert(
                "visualization_error",
                "Error generating the requested visualization",
                "error",
            )
        return jsonify(
            {
                "success": False,
                "error": "Invalid visualization request",
            },
        ), 400


def _api_table_info(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Return information about a table."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "api_table_info_not_found",
                table_name,
            )
        return jsonify({"error": f"Table {table_name} not found"}), 404

    df = app.data[table_name]

    # Get column information
    columns_info: list[dict[str, object]] = []
    columns_info.extend(
        {
            "name": col,
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].null_count()),
            "unique_count": int(df[col].drop_nulls().n_unique())
            if df[col].dtype == pl.String
            else None,
        }
        for col in df.columns
    )

    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "api_get_table_info",
            table_name,
        )

    return jsonify(
        {
            "table_name": table_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns_info,
            "available_columns": get_available_columns(df),
        },
    )


def _health_check(app: ResearchFlask) -> Response | tuple[Response, int] | str:
    """Health check endpoint."""
    if not app.health_checker:
        return jsonify(
            {"status": "unhealthy", "error": "Health checker not initialized"},
        ), 500

    try:
        health_results = app.health_checker.run_health_check()
        status_code = 200 if health_results["status"] == "healthy" else 503
        return jsonify(health_results), status_code
    except Exception:
        app.logger.exception("Health check failed")
        if app.alert_manager:
            app.alert_manager.send_alert(
                "health_check_error",
                "Health check failed",
                "error",
            )
        return jsonify({"status": "unhealthy", "error": "Health check failed"}), 500


def _metrics(app: ResearchFlask) -> Response | tuple[Response, int] | str:
    """Return performance metrics."""
    if not app.metrics_collector:
        return jsonify({"error": "Metrics collector not initialized"}), 500

    try:
        metrics_summary = app.metrics_collector.get_metrics_summary()
        return jsonify(metrics_summary)
    except Exception:
        app.logger.exception("Metrics collection failed")
        if app.alert_manager:
            app.alert_manager.send_alert(
                "metrics_error",
                "Metrics collection failed",
                "error",
            )
        return jsonify({"error": "Metrics collection failed"}), 500


def _alerts(app: ResearchFlask) -> Response | tuple[Response, int] | str:
    """Recent alerts endpoint."""
    if not app.alert_manager:
        return jsonify({"error": "Alert manager not initialized"}), 500

    try:
        recent_alerts = app.alert_manager.get_recent_alerts()
        return jsonify(recent_alerts)
    except Exception:
        app.logger.exception("Alerts are unavailable")
        return jsonify({"error": "Alerts are unavailable"}), 500


def _dashboard(app: ResearchFlask) -> Response | tuple[Response, int] | str:
    """Interactive dashboard with comprehensive data overview."""
    if not app.data:
        return render_template(
            "dashboard.html",
            tables=[],
            total_rows=0,
            total_columns=0,
            visualizations_count=0,
            table_info={},
        )

    # Calculate summary statistics
    total_rows = sum(len(df) for df in app.data.values())
    total_columns = sum(len(df.columns) for df in app.data.values())

    # Create table information
    table_info = {}
    for name, df in app.data.items():
        # Generate descriptions based on table names
        descriptions = {
            "detailed_table": ("Primary cost calculation table with all process steps"),
            "dsa__labour_prices": "Labor cost rates for sensitivity analysis",
            "dsa__test_throughput": "Test volume assumptions for DSA",
            "summary_table": "High-level cost summaries by test type",
            "at_a_glance": "Executive summary of key cost metrics",
        }

        table_info[name] = {
            "rows": len(df),
            "columns": len(df.columns),
            "description": descriptions.get(name, f"Data table: {name}"),
        }

    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "view_dashboard",
            "dashboard_page",
        )

    return render_template(
        "dashboard.html",
        tables=list(app.data.keys()),
        total_rows=total_rows,
        total_columns=total_columns,
        visualizations_count=3,  # Number of chart types available
        table_info=table_info,
    )


def _api_dashboard_cost_distribution(
    app: ResearchFlask,
) -> Response | tuple[Response, int] | str:
    """Return the cost distribution chart."""
    if not app.data or "detailed_table" not in app.data:
        return jsonify({"error": "Detailed table not found"}), 404

    df = app.data["detailed_table"]

    # Find cost columns
    cost_columns = [
        col for col in df.columns if "cost" in col.lower() or "price" in col.lower()
    ]
    if not cost_columns:
        return jsonify({"error": "No cost columns found"}), 404

    try:
        # Generate cost distribution visualization
        img_base64 = generate_visualization(df, "distribution", cost_columns[0])

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "api_dashboard_cost_dist",
                "dashboard",
            )

        return jsonify({"success": True, "image": img_base64})
    except Exception:
        app.logger.exception("Could not render the cost distribution")
        return jsonify({"error": "Could not render the cost distribution"}), 500


def _api_dashboard_top_categories(
    app: ResearchFlask,
) -> Response | tuple[Response, int] | str:
    """Return the top categories chart."""
    if not app.data or "detailed_table" not in app.data:
        return jsonify({"error": "Detailed table not found"}), 404

    df = app.data["detailed_table"]

    # Find category and cost columns
    category_columns = [col for col in df.columns if "category" in col.lower()]
    cost_columns = [
        col for col in df.columns if "cost" in col.lower() or "price" in col.lower()
    ]

    if not category_columns or not cost_columns:
        return jsonify({"error": "Required columns not found"}), 404

    try:
        # Generate top categories visualization
        img_base64 = generate_visualization(
            df,
            "category",
            cost_columns[0],
            category_columns[0],
        )

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "api_dashboard_top_cat",
                "dashboard",
            )

        return jsonify({"success": True, "image": img_base64})
    except Exception:
        app.logger.exception("Could not render the category chart")
        return jsonify({"error": "Could not render the category chart"}), 500


def _export_all_zip(app: ResearchFlask) -> Response | tuple[Response, int] | str:
    """Export all tables as a ZIP file."""
    if not app.data:
        return jsonify({"error": "No data available"}), 404

    try:
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for table_name, df in app.data.items():
                # Add CSV file
                csv_content = df.write_csv()
                zip_file.writestr(f"{table_name}.csv", csv_content)

                # Add JSON file
                json_content = df.write_json()
                zip_file.writestr(f"{table_name}.json", json_content)

        zip_buffer.seek(0)

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "export_all_zip",
                "dashboard",
            )

        return Response(
            zip_buffer.getvalue(),
            mimetype="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=microcosting_data.zip",
            },
        )
    except Exception:
        app.logger.exception("Could not create the archive")
        return jsonify({"error": "Could not create the archive"}), 500


def _generate_report(app: ResearchFlask) -> Response | tuple[Response, int] | str:
    """Generate a comprehensive PDF report."""
    if not app.data:
        return jsonify({"error": "No data available"}), 404

    try:
        # Create PDF in memory
        pdf_buffer = io.BytesIO()
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
            c.drawString(
                120,
                y_position,
                f"• {table_name}: {len(df)} rows, {len(df.columns)} columns",
            )
            y_position -= 15
            if y_position < _PDF_PAGE_BOTTOM:
                c.showPage()
                y_position = 750

        c.save()
        pdf_buffer.seek(0)

        # Log this user action
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "generate_report",
                "dashboard",
            )

        return Response(
            pdf_buffer.getvalue(),
            mimetype="application/pdf",
            headers={
                "Content-Disposition": ("attachment; filename=microcosting_report.pdf"),
            },
        )
    except ImportError:
        return jsonify({"error": "PDF generation requires reportlab package"}), 500
    except Exception:
        app.logger.exception("Could not generate the PDF report")
        return jsonify({"error": "Could not generate the PDF report"}), 500


def _export_csv(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Export table data as CSV."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "export_csv_not_found",
                table_name,
            )
        return jsonify({"error": f"Table {table_name} not found"}), 404

    df = app.data[table_name]

    # Create CSV content
    csv_content = df.write_csv()

    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "export_csv",
            table_name,
            {"rows": len(df), "columns": len(df.columns)},
        )

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table_name}.csv"},
    )


def _export_excel(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Export table data as Excel file."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "export_excel_not_found",
                table_name,
            )
        return jsonify({"error": f"Table {table_name} not found"}), 404

    df = app.data[table_name]

    # Create Excel file in memory
    output = io.BytesIO()
    book = Workbook()
    sheet = book.active
    if sheet is None:
        message = "New export workbook has no active sheet"
        raise RuntimeError(message)
    sheet.title = table_name[:31]
    sheet.append(df.columns)
    for column_number, name in enumerate(df.columns, start=1):
        sheet.cell(1, column_number, name).data_type = "s"
    for row_number, row in enumerate(df.iter_rows(), start=2):
        sheet.append(row)
        for column_number, value in enumerate(row, start=1):
            if isinstance(value, str):
                sheet.cell(row_number, column_number, value).data_type = "s"
        if all(value is None for value in row):
            # A styled blank cell serialises the row without inventing a value.
            sheet.cell(row_number, 1).number_format = "@"
    book.save(output)

    output.seek(0)

    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "export_excel",
            table_name,
            {"rows": len(df), "columns": len(df.columns)},
        )

    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={table_name}.xlsx"},
    )


def _export_json(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Export table data as JSON."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "export_json_not_found",
                table_name,
            )
        return jsonify({"error": f"Table {table_name} not found"}), 404

    df = app.data[table_name]

    # Convert to JSON
    json_data = df.write_json()

    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "export_json",
            table_name,
            {"rows": len(df), "columns": len(df.columns)},
        )

    return Response(
        json_data,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={table_name}.json"},
    )


def _export_parquet(
    app: ResearchFlask,
    table_name: str,
) -> Response | tuple[Response, int] | str:
    """Export table data as Parquet file."""
    if table_name not in app.data:
        if app.usage_analytics:
            app.usage_analytics.log_user_action(
                "anonymous",
                "export_parquet_not_found",
                table_name,
            )
        return jsonify({"error": f"Table {table_name} not found"}), 404

    df = app.data[table_name]

    # Create Parquet file in memory
    output = io.BytesIO()
    df.write_parquet(output)
    output.seek(0)

    # Log this user action
    if app.usage_analytics:
        app.usage_analytics.log_user_action(
            "anonymous",
            "export_parquet",
            table_name,
            {"rows": len(df), "columns": len(df.columns)},
        )

    return Response(
        output.getvalue(),
        mimetype="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={table_name}.parquet",
        },
    )


def main() -> None:
    """Run the web application."""
    app = create_app()

    # Run the app
    app.run(debug=False, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
