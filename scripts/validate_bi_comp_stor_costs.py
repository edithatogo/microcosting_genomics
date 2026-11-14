# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Validates the replicated 'BI - Comp+Stor Costs - VCGS' data against the original."""

import sys

import numpy as np
import pandas as pd


def validate_bi_comp_stor_costs() -> None:
    """Validate the replicated 'BI - Comp+Stor Costs - VCGS' data."""
    # Load original data, skipping headers

    # Load replicated data
    replicated_server_df = pd.read_csv("data/replicated/server_costs.csv")
    replicated_equipment_df = pd.read_csv("data/replicated/equipment_costs.csv")
    replicated_storage_df = pd.read_csv("data/replicated/storage_costs.csv")

    errors = []

    # --- Validate Server Costs ---
    server_cols = [
        "Description",
        "Source",
        "Date",
        "CPUs",
        "Cores/CPU",
        "Threads/CPU",
        "Total Cores",
        "Total Threads",
        "Memory",
        "ex-GST",
        "inc. GST",
        "3-yr",
        "5-yr",
        "Unnamed: 13",
        "Cost/CPU",
        "Cost/Core",
        "Cost/Thread",
        "Cost/GB",
        "LL",
        "UL",
        "Cost/CPU/hr",
        "Cost/Core/hr",
        "Cost/thread/hr",
        "cost/gb/hr",
        "Cost/CPU/hr.1",
        "Cost/Core/hr.1",
        "Cost/thread/hr.1",
        "cost/gb/hr.1",
        "Unnamed: 28",
    ]
    server_df_orig = pd.read_csv(
        "data/extracted/BI___CompStor_Costs___VCGS_values.csv",
        header=None,
        skiprows=2,
        names=server_cols,
    )

    server_cols_to_check = {
        "Total Cores": "Total Cores",
        "Total Threads": "Total Threads",
        "inc. GST": "inc. GST",
        "3-yr": "3-yr",
        "5-yr": "5-yr",
        "Cost/CPU": "Cost/CPU",
        "Cost/Core": "Cost/Core",
        "Cost/Thread": "Cost/Thread",
        "Cost/GB": "Cost/GB",
        "Cost/CPU/hr.1": "Cost/CPU/hr - 100%",
        "Cost/Core/hr.1": "Cost/Core/hr - 100%",
        "Cost/thread/hr.1": "Cost/thread/hr - 100%",
        "cost/gb/hr.1": "cost/gb/hr - 100%",
    }
    for orig_col, rep_col in server_cols_to_check.items():
        orig_series = server_df_orig[orig_col].iloc[0:2].astype(float)
        rep_series = replicated_server_df[rep_col].astype(float)
        if not np.allclose(
            orig_series.values,
            rep_series.values,
            rtol=1e-5,
            atol=1e-8,
            equal_nan=True,
        ):
            errors.append(
                f"Server Costs Mismatch in column {orig_col}:\nOriginal:\n"
                f"{orig_series.to_numpy()}\nReplicated:\n"
                f"{rep_series.to_numpy()}",
            )

    # --- Validate Equipment Costs ---
    equipment_cols = [
        "Equipment",
        "Brand",
        "Model",
        "Useful Life",
        "List Price (USD)",
        "List Price (EUR)",
        "List Price (AUD)",
        "Date Accessed",
        "Source",
        "Annualised cost",
        "Workflows",
        "Unnamed: 11",
        "Initial Estimate",
        "Unnamed: 13",
        "Unnamed: 14",
        "Unit Cost ($/sample)",
        "Unnamed: 16",
        "Unnamed: 17",
        "Unnamed: 18",
    ]
    equipment_df_orig = pd.read_csv(
        "data/extracted/BI___CompStor_Costs___VCGS_values.csv",
        header=None,
        skiprows=7,
        names=equipment_cols,
    )
    equipment_cols_to_check = {
        "Annualised cost": "Annualised cost",
        "Unit Cost ($/sample)": "Unit Cost ($/sample) - Initial",
        "Unnamed: 17": "Unit Cost ($/sample) - Actual (0.7)",
        "Unnamed: 18": "Unit Cost ($/sample) - Max",
    }
    # --- Validate Equipment Costs ---
    equipment_cols = [
        "Equipment",
        "Brand",
        "Model",
        "Useful Life",
        "List Price (USD)",
        "List Price (EUR)",
        "List Price (AUD)",
        "Date Accessed",
        "Source",
        "Annualised cost",
        "Workflows",
        "Unnamed: 11",
        "Initial Estimate",
        "Unnamed: 13",
        "Unnamed: 14",
        "Unit Cost ($/sample)",
        "Unnamed: 16",
        "Unnamed: 17",
        "Unnamed: 18",
    ]
    equipment_df_orig = pd.read_csv(
        "data/extracted/BI___CompStor_Costs___VCGS_values.csv",
        header=None,
        skiprows=8,
        names=equipment_cols,
        nrows=2,
    )
    equipment_cols_to_check = {
        "Annualised cost": "Annualised cost",
        "Unit Cost ($/sample)": "Unit Cost ($/sample) - Initial",
        "Unnamed: 17": "Unit Cost ($/sample) - Actual (0.7)",
        "Unnamed: 18": "Unit Cost ($/sample) - Max",
    }
    for orig_col, rep_col in equipment_cols_to_check.items():
        orig_series = pd.to_numeric(equipment_df_orig[orig_col], errors="coerce")
        rep_series = replicated_equipment_df[rep_col].astype(float)
        if not np.allclose(
            orig_series.values,
            rep_series.values,
            rtol=1e-5,
            atol=1e-8,
            equal_nan=True,
        ):
            errors.append(
                f"Equipment Costs Mismatch in column {orig_col}:\nOriginal:\n"
                f"{orig_series.to_numpy()}\nReplicated:\n"
                f"{rep_series.to_numpy()}",
            )

    # --- Validate Storage Costs ---
    storage_cols = [
        "Description",
        "Source",
        "Date",
        "Total Space (GB)",
        "ex-GST",
        "inc. GST",
        "Useable life (years)",
        "Cost/GB",
        "Cost/GB/year",
        "Cost/test",
    ]
    storage_df_orig = pd.read_csv(
        "data/extracted/BI___CompStor_Costs___VCGS_values.csv",
        header=None,
        skiprows=14,
        names=storage_cols,
        nrows=7,
    )
    storage_cols_to_check = {
        "Cost/GB": "Cost/GB",
        "Cost/GB/year": "Cost/GB/year",
        "Cost/test": "Cost/test",
    }
    for orig_col, rep_col in storage_cols_to_check.items():
        orig_series = pd.to_numeric(
            storage_df_orig[orig_col].iloc[[1, 4, 5, 6]],
            errors="coerce",
        )
        rep_series = replicated_storage_df[rep_col].astype(float)
        if not np.allclose(
            orig_series.values,
            rep_series.values,
            rtol=1e-5,
            atol=1e-8,
            equal_nan=True,
        ):
            errors.append(
                f"Storage Costs Mismatch in column {orig_col}:\nOriginal:\n"
                f"{orig_series.to_numpy()}\nReplicated:\n"
                f"{rep_series.to_numpy()}",
            )

    if errors:
        for error in errors:
            sys.stdout.write(str(error) + "\n")
        sys.stdout.write(f"\\n{len(errors)} validation errors found." + "\n")
    else:
        sys.stdout.write("Validation successful! No discrepancies found." + "\n")


if __name__ == "__main__":
    validate_bi_comp_stor_costs()
