"""Validate calculated costs against the original Excel data."""

from pathlib import Path

import numpy as np
import pandas as pd


def validate_calculations():
    """
    Validates the calculated costs against the original Excel sheet.
    """
    # Load the calculated data
    try:
        calculated_df = pd.read_parquet(
            Path(__file__).resolve().parents[0]
            / "data"
            / "calculated_costs_tidy.parquet"
        )
    except FileNotFoundError:
        print("Error: calculated_costs_tidy.parquet not found.")
        print("Please run replicate_calculations.py to generate the file.")
        return

    # Load the original data from the Excel sheet
    file_path = (
        Path(__file__).resolve().parents[0]
        / "data"
        / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
    try:
        original_df_raw = pd.read_excel(
            file_path, sheet_name="1. Detailed Table", header=None
        )
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return

    # Data cleaning and preparation for the original data
    header = original_df_raw.iloc[0].astype(str).str.replace("nan", "")
    sub_header = original_df_raw.iloc[1].astype(str).str.replace("nan", "")
    new_header = [
        f"{h}_{sh}".strip("_") if h or sh else f"Unnamed_{i}"
        for i, (h, sh) in enumerate(zip(header, sub_header))
    ]
    original_df = original_df_raw[2:].copy()
    original_df.columns = new_header
    original_df.rename(
        columns={
            "Test": "Test_Type",
            "Category": "Cost_Category",
            "Sub-Category": "Cost_Sub_Category",
            "Step": "Cost_Step",
            "Unit Cost (AUD $/unit)": "original_cost",
        },
        inplace=True,
    )

    # Sum the calculated costs
    calculated_df["calculated_total_cost"] = calculated_df[
        ["unit_cost_labour", "unit_cost_equipment", "unit_cost_consumables"]
    ].sum(axis=1)

    # Merge the two dataframes for comparison
    comparison_df = pd.merge(
        original_df,
        calculated_df,
        on=["Test_Type", "Cost_Category", "Cost_Sub_Category", "Cost_Step"],
        how="left",
    )

    # Convert cost columns to numeric, coercing errors
    comparison_df["original_cost"] = pd.to_numeric(
        comparison_df["Unit Cost (AUD $/unit)"], errors="coerce"
    )
    comparison_df["calculated_total_cost"] = pd.to_numeric(
        comparison_df["calculated_total_cost"], errors="coerce"
    )

    # Fill NaN values for comparison
    comparison_df.fillna(0, inplace=True)

    # --- Validation ---
    discrepancies = []
    tolerance = 1e-6  # Tolerance for floating point comparison

    for index, row in comparison_df.iterrows():
        original_cost = row["original_cost"]
        calculated_cost = row["calculated_total_cost"]

        if not np.isclose(original_cost, calculated_cost, atol=tolerance):
            discrepancy = {
                "row": index + 2,  # Account for header rows
                "Test_Type": row["Test_Type"],
                "Cost_Category": row["Cost_Category"],
                "Cost_Sub_Category": row["Cost_Sub_Category"],
                "Cost_Step": row["Cost_Step"],
                "original_cost": original_cost,
                "calculated_cost": calculated_cost,
                "difference": original_cost - calculated_cost,
            }
            discrepancies.append(discrepancy)

    # --- Reporting ---
    print("--- Validation Report ---")
    if discrepancies:
        print(f"Found {len(discrepancies)} discrepancies:")
        discrepancies_df = pd.DataFrame(discrepancies)
        print(discrepancies_df.to_string())
    else:
        print(
            "No discrepancies found. All calculations match the original Excel sheet."
        )

    print("\n--- Summary ---")
    print(f"Total rows validated: {len(comparison_df)}")
    print(f"Total discrepancies found: {len(discrepancies)}")
    print("---------------------")


if __name__ == "__main__":
    validate_calculations()
