# Gemini Project: unimelb-phd-phase-1

This document outlines the project's roadmap, my understanding of the project, and my planned next steps.

## Project Summary

This project aims to reverse-engineer a complex Excel-based microcosting model for genomic testing in rare diseases. The goal is to create a transparent, maintainable, and extensible version of the model in Python. This will involve parsing Excel formulas, identifying calculation patterns, and replicating the model's logic in a structured and well-documented Python application.

## My Understanding

The core of this project is a large Excel file containing a "detailed" sheet with hundreds of rows of data and complex calculations. The calculations are not well-documented, and the formulas are repeated many times, making the model difficult to understand and maintain. My task is to create a Python-based replacement for this model that is more robust and easier to work with.

## Roadmap

The project is divided into the following phases:

### Phase 1: Data Extraction and Initial Analysis (Completed)

- [x] **File Identification:** Locate and confirm the primary Excel file and the "detailed" sheet.
- [x] **Lab Book Creation:** Create `LAB_BOOK.md` to document findings.
- [x] **Initial Data Load:** Load the data into pandas and openpyxl to inspect its structure.
- [x] **Structural Analysis:** Map the layout of the spreadsheet and categorize the columns.

### Phase 2: Formula Parsing and Pattern Recognition (Completed)

- [x] **Formula Extraction:** Systematically extract all unique formulas.
- [x] **Formula Parsing:** Develop a Python function to parse Excel formulas.
- [x] **Pattern Identification:** Analyze the parsed formulas to identify recurring patterns.
- [x] **Semantic Analysis:** Investigate the meaning behind the calculations.

### Phase 3 (Revised): Calculation Replication and Validation (In Progress)

- [x] **Step 1: Establish Ground Truth:** Create an immutable dataset of inputs and expected outputs from the original Excel file to serve as the standard for validation.
- [x] **Step 2: Engineer the Data Access Layer:** Using Test-Driven Development (TDD), fix the data loading mechanism in the `CalculationEngine` to correctly handle the complex Excel headers.
- [x] **Step 3: Implement the Interpreter with Memoization:** Implement the `execute_formula` method as a recursive, tree-walking interpreter with a caching layer (memoization) to ensure efficient calculation.
- [x] **Step 4: Refactor to Strategy Pattern:** Refactor the calculation logic into separate "strategy" classes for each formula type to improve modularity and extensibility.
- [ ] **Step 5: Build and Run the Validation Harness:** Create a script to rigorously compare the Python engine's output against the ground truth, quantifying any errors.

### Phase 4: Abstraction and Code Refactoring (In Progress)

- [ ] **Code Generalization:** Refactor the Python functions to be more abstract and reusable.
- [ ] **Configuration:** Externalize model parameters into a configuration file.
- [ ] **Documentation:** Create comprehensive documentation for the new Python library.
- [ ] **Implement Remaining Strategies:** Add support for `IF`, `IFERROR`, and `VLOOKUP` formulas.
- [ ] **Refactor CalculationEngine:** Improve the modularity and testability of the `CalculationEngine`.
- [ ] **Create Validation Script:** Develop a script to compare the Python-calculated results with the original Excel outputs.

## Next Steps

The next steps for this project are outlined in the `agents.md` file.
For a summary of the Excel workbook's sheets and how they relate to the detailed table see [docs/table_overview.md](docs/table_overview.md).
