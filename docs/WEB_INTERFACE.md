# Web Interface Documentation

The Web Interface provides a user-friendly way to explore microcosting data, visualize results, and interact with the analysis toolkit through a web browser.

## Overview

The web interface is built using Flask and provides a responsive, interactive experience for exploring microcosting data. It includes features for data browsing, visualization, and scenario analysis.

## Architecture

The web interface follows a modular architecture with the following key components:

### Core Components

1. **Flask Application** - Main web application server
2. **HTML Templates** - Jinja2 templates for rendering pages
3. **Static Assets** - CSS, JavaScript, and images
4. **API Endpoints** - RESTful APIs for data access
5. **Visualization Utilities** - Server-side chart generation

### Design Principles

- **Responsiveness**: Mobile-friendly design that works on all devices
- **Interactivity**: Dynamic user interface with real-time updates
- **Performance**: Efficient data loading and rendering
- **Accessibility**: WCAG-compliant interface design

## Key Features

### Data Exploration
Browse and explore microcosting data through an intuitive interface:

```python
# In web.py
@app.route("/")
def index():
    """Main page showing available data tables."""
    tables = list(app.data.keys()) if app.data else []
    return render_template("index.html", tables=tables)
```

Features include:
- Table listing and navigation
- Data preview with pagination
- Column information and statistics
- Export capabilities

### Interactive Visualizations
Generate and explore visualizations dynamically:

```python
@app.route("/api/generate_viz/<table_name>")
def api_generate_viz(table_name):
    """API endpoint to generate a visualization for a table."""
    # Generate visualization based on parameters
    img_base64 = generate_visualization(df, viz_type, column_name, category_column)

    return jsonify(
        {
            "success": True,
            "image": img_base64,
            "table_name": table_name,
            "viz_type": viz_type,
        }
    )
```

Visualization types:
- Cost distribution charts
- Category comparison charts
- Top cost item visualizations
- Custom chart configurations

### Scenario Analysis Interface
Interactive tools for scenario analysis:

```python
@app.route("/visualize")
def visualize():
    """Page for visualizations."""
    tables = list(app.data.keys()) if app.data else []
    return render_template("visualize.html", tables=tables)
```

Features include:
- Parameter selection for scenarios
- Real-time visualization updates
- Comparison tools
- Export functionality

## Usage

### Running the Web Interface

```bash
# Run the web interface
python scripts/run_web.py
```

Access the application at: http://127.0.0.1:5000

### Web Interface Components

#### Home Page
The home page provides an overview of available data tables:
- List of all available tables
- Quick access to data exploration
- Links to visualization tools
- Navigation to other sections

#### Data Table View
Detailed view of individual data tables:
- Tabular data display with pagination
- Column filtering and sorting
- Data statistics and information
- Export to CSV functionality

#### Visualization Interface
Interactive visualization tools:
- Dynamic chart generation
- Multiple chart types
- Parameter customization
- Image download

### API Endpoints

The web interface provides RESTful API endpoints for programmatic access:

#### Table Data Endpoints
- `GET /api/tables` - List available tables
- `GET /api/table/<table_name>` - Get table data
- `GET /api/table_info/<table_name>` - Get table information

#### Visualization Endpoints
- `GET /api/visualize/<table_name>` - Get visualization data
- `GET /api/generate_viz/<table_name>` - Generate visualization image

#### Example API Usage

```javascript
// Get list of available tables
fetch('/api/tables')
    .then(response => response.json())
    .then(data => {
        console.log('Available tables:', data);
    });

// Generate a visualization
fetch('/api/generate_viz/Detailed_Table?type=distribution&column=Cost')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Display the visualization
            document.getElementById('vizContainer').innerHTML = 
                `<img src="data:image/png;base64,${data.image}" alt="Visualization">`;
        }
    });
```

## Frontend Components

### HTML Templates
The web interface uses Jinja2 templates for dynamic content rendering:

#### Base Template
- Common layout and navigation
- CSS and JavaScript inclusion
- Header and footer structure

#### Page Templates
- `index.html` - Home page
- `table.html` - Data table view
- `visualize.html` - Visualization interface

### CSS Styling
Custom CSS provides a consistent, professional appearance:

```css
/* In static/style.css */
:root {
  --primary-color: #007bff;
  --secondary-color: #6c757d;
  --success-color: #28a745;
}

.card {
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
  border: 1px solid rgba(0, 0, 0, 0.125);
}
```

### JavaScript Functionality
Custom JavaScript enhances interactivity:

```javascript
// In static/scripts.js
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Form handling
document.getElementById('visualizationForm').addEventListener('submit', function(e) {
    e.preventDefault();
    // Handle form submission
});
```

## Performance Considerations

### Data Loading
- Efficient data loading from Parquet files
- Caching of frequently accessed data
- Pagination for large datasets
- Lazy loading where appropriate

### Visualization Generation
- Server-side chart generation
- Base64 encoding for image transfer
- Memory management for chart objects
- Caching of generated visualizations

### Response Optimization
- JSON responses for API endpoints
- Compression of large responses
- Efficient database queries
- Connection pooling

## Security Considerations

### Input Validation
- Sanitization of user inputs
- Validation of API parameters
- Protection against injection attacks
- File upload restrictions

### Access Control
- No external network access required
- Local file system access only
- Secure configuration management
- Error handling without information disclosure

## Customization

### Theming
Customize the appearance through CSS:

```css
/* Custom theme in static/style.css */
body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f5f7fa;
}
```

### Layout Modifications
Modify templates to change page structure:

```html
<!-- In templates/custom.html -->
{% extends "base.html" %}

{% block content %}
<div class="custom-layout">
    <!-- Custom content -->
</div>
{% endblock %}
```

### Adding New Features
Extend the web interface with new functionality:

```python
# Add new route in web.py
@app.route("/custom-feature")
def custom_feature():
    """Custom feature endpoint."""
    return render_template("custom_feature.html")
```

## Integration with Other Components

### Data Management
The web interface integrates with the data management system:
- Loads data through DataManager
- Uses prepared Parquet files for performance
- Supports multiple data formats

### Calculation Engine
Integration with the calculation engine:
- Displays calculated results
- Supports real-time calculations
- Shows error information

### Visualization Tools
Uses advanced visualization capabilities:
- Interactive Plotly charts
- Server-side chart generation
- Multiple export formats

## Testing

The web interface includes tests for:
- Route handling
- API endpoint responses
- Template rendering
- JavaScript functionality

Run web interface tests with:
```bash
python -m pytest tests/test_web.py
```

## Deployment

### Production Deployment
For production deployment:

1. Use a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 unimelb_phd_phase_1.web:app
```

2. Configure reverse proxy (nginx, Apache)

3. Set up SSL certificates

4. Configure environment variables

### Environment Configuration
Set environment variables for production:

```bash
export FLASK_ENV=production
export FLASK_DEBUG=False
```

## API Reference

### Flask Application Functions

#### `create_app(data_dir=None)`
Create and configure the Flask application.

**Parameters:**
- `data_dir` (str or Path, optional): Path to the data directory

**Returns:**
- Flask: Configured Flask application

#### `main()`
Main function to run the web application.

### Web Routes

#### `GET /`
Main page showing available data tables.

#### `GET /table/<table_name>`
Show a specific data table.

#### `GET /api/tables`
API endpoint to get list of available tables.

**Returns:**
- JSON: List of table names

#### `GET /api/table/<table_name>`
API endpoint to get table data.

**Returns:**
- JSON: Table data with columns and records

#### `GET /visualize`
Page for visualizations.

#### `GET /api/visualize/<table_name>`
API endpoint to generate visualization data for a table.

**Returns:**
- JSON: Visualization data including available columns

#### `GET /api/generate_viz/<table_name>`
API endpoint to generate a visualization for a table.

**Query Parameters:**
- `type` (str): Visualization type (distribution, category, top)
- `column` (str, optional): Column to visualize
- `category` (str, optional): Category column for grouped visualizations

**Returns:**
- JSON: Base64 encoded PNG image