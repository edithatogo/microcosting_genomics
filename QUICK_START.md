# Quick Start Guide

Get up and running with the Genomics Microcosting Analysis Toolkit in under 10 minutes.

## Prerequisites

- Python 3.8 or later
- Excel workbook with microcosting data (optional for basic testing)

## 🚀 Quick Installation

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/edithatogo/microcosting_genomics.git
cd microcosting_genomics

# Install in development mode with all dependencies
pip install -e .[dev]
```

### 2. Verify Installation

```bash
# Check that everything is working
python -c "from src.genomics_microcosting.calculation_engine import CalculationEngine; print('✅ Installation successful!')"
```

## 📊 Basic Usage

### Option 1: Web Interface (Recommended for Exploration)

```bash
# Start the web server
python -m src.genomics_microcosting.web

# Open your browser to: http://127.0.0.1:5000
```

**What you'll see:**

- Interactive dashboard with data overview
- Table browser for exploring datasets
- Export functionality (CSV, Excel, JSON, Parquet)
- Real-time data visualization

### Option 2: Command Line Analysis

```bash
# Run validation against your Excel data
python validate_engine.py

# Prepare data from Excel workbooks
python prepare_data.py

# Run all tests
python -m pytest tests/ -v
```

## 🔧 Configuration (Optional)

If you have Excel workbooks to analyze:

1. **Update config.yaml:**

   ```yaml
   workbooks:
     main:
       path: "path/to/your/workbook.xlsx"
       sheets:
         "Detailed Table":
           header_rows: 2
           skip_rows: 1
   ```

2. **Prepare your data:**

   ```bash
   python prepare_data.py
   ```

## 📈 Common Workflows

### 1. Data Exploration

```python
from src.genomics_microcosting.data_manager import DataManager

# Load and explore data
dm = DataManager()
tables = dm.list_available_tables()
print("Available tables:", tables)

# Load specific table
df = dm.load_table("detailed_table")
print(df.head())
```

### 2. Run Calculations

```python
from src.genomics_microcosting.calculation_engine import CalculationEngine
from src.genomics_microcosting.sheet_manager import SheetManager

# Initialize components
sheet_manager = SheetManager()
engine = CalculationEngine(sheet_manager)

# Execute formulas
result = engine.execute_formula("=SUM(A1:A10)", "Sheet1", "B1")
print("Result:", result)
```

### 3. Generate Reports

```python
from src.genomics_microcosting.web import create_app

# Create web app instance
app = create_app()

# Export data programmatically
with app.app_context():
    # Access export functionality
    pass
```

## 🧪 Testing Your Setup

### Run Basic Tests

```bash
# Run core calculation tests
python -m pytest tests/test_calculation_engine.py -v

# Run data management tests
python -m pytest tests/test_data_manager.py -v

# Run all tests with coverage
python -m pytest --cov=src/genomics_microcosting --cov-report=term-missing
```

### Validate Against Excel

```bash
# If you have Excel data configured
python validate_engine.py
```

## 🎯 Next Steps

### For Researchers

1. **Explore the web interface** - Use the dashboard for data visualization
2. **Configure your data sources** - Update `config.yaml` with your Excel files
3. **Run sensitivity analyses** - Use the advanced scenario modeling features
4. **Generate reports** - Export results in multiple formats

### For Developers

1. **Read the API documentation** - See `docs/API_REFERENCE.md`
2. **Explore the plugin system** - See `docs/PLUGIN_SYSTEM.md`
3. **Contribute features** - Follow `CONTRIBUTING.md`
4. **Run the full test suite** - Ensure all tests pass

## 📚 Additional Resources

- **Full Documentation**: `docs/README.md`
- **API Reference**: `docs/API_REFERENCE.md`
- **Troubleshooting**: `docs/troubleshooting_guide.md`
- **Tutorials**: `docs/tutorial_series.md`
- **Development Guide**: `docs/DEVELOPMENT_GUIDE.md`

## 🆘 Getting Help

- **Check the troubleshooting guide**: `docs/troubleshooting_guide.md`
- **Review error logs**: Check `logs/` directory
- **Run diagnostics**: Use the web interface health checks
- **Community support**: Check GitHub issues

---

**Time to complete**: ~5-10 minutes  
**Skills required**: Basic Python and command line knowledge  
**Next recommended step**: Explore the web interface at `http://127.0.0.1:5000`
