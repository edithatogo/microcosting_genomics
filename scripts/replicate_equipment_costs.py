# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Replicate equipment cost calculations using the extracted CSV data."""

import sys
from pathlib import Path

import numpy as np
import numpy_financial as npf
import pandas as pd

# Load the data, skipping initial rows and setting a header row
DATA_DIR = Path(__file__).resolve().parents[0] / "data" / "extracted"
df = pd.read_csv(
    DATA_DIR / "Eq - Costs and Usage - VCGS_values.csv",
    header=3,
    dtype=str,
)

# Drop empty rows
df = df.dropna(how="all")
df = df.reset_index(drop=True)

# Clean up column names
# The header has some issues due to merged cells in Excel.
# Let's create a cleaned-up list of column names.
columns = [
    "Equipment",
    "Description",
    "Brand",
    "Model",
    "Useful Life",
    "List Price (USD)",
    "List Price (EUR)",
    "List Price (AUD)",
    "Date Accessed",
    "Source",
    "Annualised cost",
    "Present value",
    "Workflows WES/Panel",
    "Workflows WGS",
    "Initial Estimate Total Samples per Year",
    "Initial Estimate 0.7",
    "Initial Estimate Max",
    "Theoretical 50x WES",
    "Theoretical 0.8",
    "Theoretical 0.4",
    "Theoretical Comment",
    "50x WES Max",
    "50x WES 0.7",
    "50x WES Comment",
    "80x WES Max",
    "80x WES 0.7",
    "30x Genomes Estimate",
    "30x Genomes Source",
    "30x Genomes Comment",
    "30x Genomes Max",
    "30x Genomes 70%",
    "Cost per sample LL",
    "Cost per sample MP",
    "Cost per sample UL",
]
# There are more columns in the file, but we'll only name the ones we need for now
df.columns = columns[: len(df.columns)]

# Convert relevant columns to numeric, coercing errors to NaN
numeric_cols = ["Useful Life", "List Price (AUD)", "Annualised cost", "Present value"]
for col in numeric_cols:
    # Remove any non-numeric characters (except for the decimal point)
    if df[col].dtype == "object":
        df[col] = df[col].str.replace(r"[^0-9.-]", "", regex=True)
    df[col] = pd.to_numeric(df[col], errors="coerce")


# Replicate the 'Annualised cost' calculation: =H5/E5
df["Calculated Annualised cost"] = df["List Price (AUD)"] / df["Useful Life"]

# Replicate the 'Present value' calculation: "=PMT(4.52%, E5, -H5)"
# The rate is 4.52%
rate = 0.0452
df["Calculated Present value"] = df.apply(
    lambda row: (
        npf.pmt(rate, row["Useful Life"], -row["List Price (AUD)"])
        if pd.notna(row["Useful Life"]) and pd.notna(row["List Price (AUD)"])
        else np.nan
    ),
    axis=1,
)

# Replicate 'Cost per sample LL': =K5/P8
# K is 'Annualised cost', P is 'Initial Estimate Total Samples per Year'
# This calculation has a fixed divisor from another row, which makes it tricky.
# For now, we will just show the first few rows of the main calculations.

sys.stdout.write("Cleaned Data:" + "\n")
sys.stdout.write(str(df.head()) + "\n")


sys.stdout.write("\nData with Calculated Columns:" + "\n")
sys.stdout.write(
    str(
        df[
            [
                "List Price (AUD)",
                "Useful Life",
                "Annualised cost",
                "Calculated Annualised cost",
                "Present value",
                "Calculated Present value",
            ]
        ].head(),
    )
    + "\n",
)
