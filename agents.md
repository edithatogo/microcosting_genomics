# Next Steps for Agents

This document outlines the next steps for the Gemini agents working on this project, based on the revised plan for Phase 3.

## Agent Task: Implement and Validate the Calculation Engine

The overall goal is to build a robust and validated Python-based calculation engine that accurately replicates the original Excel model.

### The Plan:

1.  **Establish Ground Truth (Data Science Focus):**
    *   **Priority:** This is the immediate first step.
    *   **Action:** Create a new script (e.g., `prepare_data.py`).
    *   **Task:** This script must read the `1. Detailed Table` from the source Excel file and extract two key components:
        1.  The input columns required for calculations.
        2.  The final calculated "Unit Cost" columns, which represent the expected outputs.
    *   **Output:** Save this data as an immutable `ground_truth.parquet` file in the `data/prepared/` directory. This dataset is the gold standard for all future validation.

2.  **Engineer the Data Access Layer (Software Engineering Focus):**
    *   **Priority:** Second, after establishing the ground truth.
    *   **Method:** Use Test-Driven Development (TDD).
    *   **Action:**
        1.  In `tests/test_calculation_engine.py`, write a new, specific test that asserts the correct parsing of the multi-level headers into a clean pandas DataFrame. This test should fail initially.
        2.  Modify the `_load_sheet` method in `unimelb_phd_phase_1/calculation_engine.py` until the new test passes, ensuring the data loading is robust.

3.  **Implement and Refactor the Interpreter (CS & SE Focus):**
    *   **Priority:** Third, after the data loader is fixed.
    *   **Action:**
        1.  **Memoization:** Add a caching dictionary to the `CalculationEngine` to store and retrieve previously calculated cell values.
        2.  **Strategy Pattern:** Create a new module (`unimelb_phd_phase_1/strategies.py`) and implement a separate strategy class for each formula type (`MultiplyStrategy`, `SumStrategy`, etc.).
        3.  **Interpreter:** Refactor the `execute_formula` method to be a clean, recursive interpreter that delegates the actual computation to the appropriate strategy object.

4.  **Validate the Engine (Data Science Focus):**
    *   **Priority:** Last, once the engine is fully implemented.
    *   **Action:** Create a `validate_engine.py` script that:
        1.  Loads the `ground_truth.parquet` data.
        2.  Uses the `CalculationEngine` to compute the results based on the inputs.
        3.  Compares the engine's output to the ground truth output, calculating and logging any absolute or percentage errors.
        4.  Produces a final validation summary.
