# Tutorial Series: Common Workflows

This tutorial series provides step-by-step instructions for common workflows in the Genomics Microcosting Project.

## Tutorial 1: Data Preparation Workflow

This tutorial covers the complete data preparation process from raw Excel workbooks to cleaned datasets ready for analysis.

### Prerequisites
- Raw Excel workbook files in the project directory
- Configuration file (`config.yaml`) with workbook and sheet definitions

### Step 1: Configure Data Sources

First, ensure your [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml) file is properly configured with the paths to your Excel workbooks and sheet definitions:

```yaml
workbooks:
  main:
    path: "path/to/your/workbook.xlsx"
    sheets:
      "Detailed Table":
        header_rows: 2
        skip_rows: 1
      "Cost Driver Analysis":
        header_rows: 1
        skip_rows: 0
```

### Step 2: Run Data Preparation

Execute the data preparation script to convert Excel sheets to cleaned Parquet and CSV files:

```bash
python prepare_data.py
```

This will:
1. Read each configured sheet from the Excel workbook
2. Parse headers and clean data
3. Convert text values to numeric where possible
4. Save cleaned data as both Parquet and CSV files in the `data/prepared` directory

### Step 3: Verify Prepared Data

Check that the prepared data files were created successfully:

```bash
ls data/prepared/
```

You should see Parquet and CSV files for each configured sheet.

## Tutorial 2: Running Cost Analysis

This tutorial covers how to run the core cost analysis using the calculation engine.

### Prerequisites
- Prepared data files from Tutorial 1
- Properly configured analysis parameters

### Step 1: Configure Analysis Parameters

Ensure your analysis configuration is set up in [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml):

```yaml
analysis:
  default_sheet: "Detailed Table"
  calculation_precision: 2
  error_handling: "graceful"
```

### Step 2: Run Basic Analysis

Execute the analysis script:

```bash
python run_analysis.py
```

This will:
1. Load the prepared data
2. Extract unit cost values
3. Fit a gamma distribution to the data
4. Perform Monte Carlo simulation
5. Calculate centiles for cost estimates

### Step 3: Review Results

The analysis output will display:
- Distribution parameters
- Centile values (2.5th, 50th, 97.5th percentiles)
- Status messages about the analysis process

## Tutorial 3: Validating Calculation Engine

This tutorial covers how to validate the calculation engine against ground truth data.

### Prerequisites
- Prepared data files
- Ground truth data file (`data/prepared/ground_truth.parquet`)

### Step 1: Prepare Ground Truth Data

If you don't have ground truth data, you may need to create it manually or obtain it from a validated source. The ground truth file should contain the expected results for validation.

### Step 2: Run Validation

Execute the validation script:

```bash
python validate_engine.py
```

This will:
1. Load the ground truth data
2. Run the calculation engine
3. Compare calculated results with ground truth
4. Report any significant errors

### Step 3: Analyze Validation Results

The validation output will show:
- Summary statistics of differences
- Significant errors (differences > 0.01)
- Error counts and magnitudes

## Tutorial 4: Advanced Analysis Workflows

This tutorial covers more advanced analysis workflows including sensitivity analysis, PSA, and VOI.

### Prerequisites
- All previous tutorials completed
- Advanced analysis modules installed

### Step 1: Run Sensitivity Analysis

Execute the DSA (Deterministic Sensitivity Analysis):

```bash
python -m unimelb_phd_phase_1.dsa_analysis
```

### Step 2: Run Probabilistic Sensitivity Analysis

Execute the PSA:

```bash
python -m unimelb_phd_phase_1.psa_analysis
```

### Step 3: Run Value of Information Analysis

Execute the VOI analysis:

```bash
python -m unimelb_phd_phase_1.voi_analysis
```

### Step 4: Generate Comprehensive Reports

Create detailed analysis reports:

```bash
python -m unimelb_phd_phase_1.comprehensive_reporting
```

## Tutorial 5: Using the Web Interface

This tutorial covers how to use the web interface for interactive analysis.

### Prerequisites
- All data preparation completed
- Web dependencies installed

### Step 1: Start the Web Server

Launch the web interface:

```bash
python -m unimelb_phd_phase_1.web
```

### Step 2: Access the Interface

Open your web browser and navigate to `http://localhost:5000`

### Step 3: Use Web Features

The web interface provides:
- Table browsing and visualization
- Interactive data exploration
- Real-time calculation results
- Export capabilities

## Tutorial 6: Security Management

This tutorial covers how to manage security features in the system.

### Prerequisites
- Understanding of role-based access control concepts

### Step 1: Set Up User Authentication

Authenticate a user and assign roles:

```python
from unimelb_phd_phase_1.security import AccessControlManager

access_control = AccessControlManager()
access_control.authenticate_user("researcher")
access_control.add_user_to_role("researcher", "analyst")
```

### Step 2: Protect Sensitive Functions

Use the permission decorator to protect functions:

```python
@access_control.require_permission("configure_system")
def update_configuration(new_config):
    # This function requires admin privileges
    pass
```

### Step 3: Audit Security Events

Log security-relevant events:

```python
from unimelb_phd_phase_1.security import AuditTrail

audit_trail = AuditTrail("logs/audit.log")
audit_trail.log_event(
    "data_access", "user123", "sensitive_data.xlsx", "Accessed cost data", True
)
```

### Step 4: Secure Configuration Storage

Store sensitive configuration data securely:

```python
from unimelb_phd_phase_1.security import SecureConfigStorage

storage = SecureConfigStorage(
    "configs/secure_config.json", encryption_key="my_secret_key"
)
storage.save_config({"api_key": "secret_key", "database_url": "postgresql://..."})
```

## Tutorial 7: Performance Optimization

This tutorial covers how to optimize performance for large datasets.

### Prerequisites
- Large dataset for testing
- Performance monitoring tools

### Step 1: Run Performance Benchmarking

Execute the benchmarking framework:

```bash
python -m unimelb_phd_phase_1.benchmarking_analysis
```

### Step 2: Monitor Memory Usage

Use the memory monitoring tools:

```python
from unimelb_phd_phase_1.performance import MemoryMonitor

monitor = MemoryMonitor()
monitor.start_monitoring()
# Run your analysis here
monitor.stop_monitoring()
print(f"Peak memory usage: {monitor.get_peak_memory()} MB")
```

### Step 3: Profile Code Performance

Use the profiling tools to identify bottlenecks:

```bash
python scripts/profile_and_optimize.py
```

## Tutorial 8: Error Handling and Recovery

This tutorial covers how to handle errors gracefully and implement recovery mechanisms.

### Prerequisites
- Understanding of error handling concepts

### Step 1: Implement Graceful Degradation

Use the error handling framework:

```python
from unimelb_phd_phase_1.error_handling import GracefulDegradationHandler

handler = GracefulDegradationHandler()
try:
    # Risky operation
    result = perform_analysis()
except Exception as e:
    result = handler.handle_missing_data_source(e, "alternative_data_source")
```

### Step 2: Use Checkpoint/Restart

Implement checkpointing for long-running analyses:

```python
from unimelb_phd_phase_1.error_handling import CheckpointManager

checkpoint = CheckpointManager("analysis_checkpoint.pkl")
if checkpoint.exists():
    state = checkpoint.load()
else:
    state = initialize_analysis()
    
# Perform analysis steps
state = process_step_1(state)
checkpoint.save(state)

state = process_step_2(state)
checkpoint.save(state)
```

### Step 3: Validate Inputs

Use comprehensive input validation:

```python
from unimelb_phd_phase_1.input_validation import InputValidator

validator = InputValidator()
try:
    validator.validate_dataframe(df, expected_columns=["A", "B", "C"])
    validator.validate_numeric_value(value, min_value=0, max_value=1000)
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Best Practices

### Data Management
- Always validate data after preparation
- Keep backups of raw data
- Document data transformations

### Security
- Never commit sensitive configuration to version control
- Regularly review user permissions
- Monitor audit logs for suspicious activity

### Performance
- Profile code before optimization
- Monitor memory usage for large datasets
- Use appropriate data types to minimize memory footprint

### Error Handling
- Implement graceful degradation for missing data
- Use checkpoint/restart for long-running analyses
- Log errors with sufficient context for debugging

## Troubleshooting

### Common Issues

1. **Data Preparation Failures**: Check that Excel files are not open in other applications and that paths in config.yaml are correct.

2. **Analysis Errors**: Verify that all required sheets are available and that data formats match expectations.

3. **Validation Failures**: Ensure ground truth data is up to date and matches the current analysis version.

4. **Security Issues**: Check that users have appropriate roles assigned and that audit logs are being written.

### Getting Help

- Check the documentation in the `docs/` directory
- Review error messages and logs
- Run unit tests to verify component functionality
- Contact the development team for support