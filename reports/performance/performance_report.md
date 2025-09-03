# Performance Analysis Report
Generated on: 2025-09-03 19:10:07

## Performance Profiling Results

| Operation | Calls | Avg Time (s) | Max Time (s) | Memory (MB) | Errors |
|-----------|-------|--------------|--------------|-------------|--------|
| load_prepared_data | 1 | 0.1135 | 0.1135 | 19.98 | 0 |
| initialize_engine | 1 | 7.5982 | 7.5982 | 1004.52 | 0 |
| run_engine | 1 | 87.6958 | 87.6958 | -16.27 | 0 |

## Data Optimization Results

| Table | Original (MB) | Optimized (MB) | Savings (MB) | Savings (%) | Time (s) |
|-------|---------------|----------------|--------------|-------------|----------|
| 3._estimates | 0.02 | 0.01 | 0.01 | 49.7 | 0.007 |
| 2._labor_prices | 0.03 | 0.02 | 0.02 | 49.8 | 0.006 |
| detailed_table_values | 0.29 | 0.25 | 0.04 | 13.8 | 0.006 |
| detailed_table_formulas | 1.01 | 1.01 | 0.00 | 0.0 | 0.017 |
| ground_truth | 0.27 | 0.15 | 0.12 | 44.4 | 0.004 |
| dsa__labour_prices | 0.03 | 0.02 | 0.02 | 49.8 | 0.006 |
| detailed_table | 0.27 | 0.15 | 0.12 | 44.4 | 0.004 |
| dsa__test_throughput | 0.02 | 0.01 | 0.01 | 49.7 | 0.004 |
| **TOTAL** | **1.94** | **1.61** | **0.33** | **17.1** | **0.054** |
