# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Replicate the labour cost calculations using the extracted CSV data.

The required CSV files are stored in the repository ``data`` directory which is
located at ``Path(__file__).resolve().parents[0] / 'data'``.
"""

import sys
from pathlib import Path

import pandas as pd

# Load the data, skipping the first row and using the second row as the header
DATA_DIR = Path(__file__).resolve().parents[0] / "data" / "extracted"
file_path = DATA_DIR / "Labour - Costs - VCGS_values.csv"
df = pd.read_csv(file_path, header=1)

# Drop empty rows
df = df.dropna(how="all")

# Clean up column names
# The header has some issues due to merged cells in Excel.
# Let's create a cleaned-up list of column names.
columns = [
    "Jurisdiction",
    "Personnel type",
    "Label",
    "Award",
    "Grade(s)",
    "Distribution desc",
    "References",
    "Rate of Pay (weekly, 38h) desc",
    "Year",
    "Superannuation Rate (%)",
    "Hours per week",
    "Average productive time (%)",
    "Average Penalties %",
    "Public Holiday Penalty Percentage",
    "Private Practice Loading",
    "Attraction and Retention Allowance",
    "Sick Leave Percentage",
    "Professional Development Allowance",
    "Annual Leave Entitlement (Weeks)",
    "Annual Leave Loading (%)",
    "Indexation per annum (%)",
    "Base Salary LL",
    "Base Salary Mid-point",
    "Base Salary UL",
    "Base Salary + Costs LL",
    "Base Salary + Costs Mid-point",
    "Base Salary + Costs UL",
    "Base Salary + Costs (hourly) LL",
    "Base Salary + Costs (hourly) Mid-point",
    "Base Salary + Costs (hourly) UL",
]
df.columns = columns

# Display the first few rows of the cleaned data
sys.stdout.write("Cleaned Data:" + "\n")
sys.stdout.write(str(df.head()) + "\n")

# Replicate the calculations
# Formula for 'Base Salary Mid-point' is =V3+((X3-V3)/2)
# In our dataframe, V is 'Base Salary LL' and X is 'Base Salary UL'
df["Calculated Base Salary Mid-point"] = df["Base Salary LL"] + (
    (df["Base Salary UL"] - df["Base Salary LL"]) / 2
)

# Formula for 'Base Salary + Costs LL' is
# =(V3+(V3*$J3)+(V3*$M3)+(V3*$N3)+(V3*$O3)+(V3*$P3)+(V3*$Q3)+($R3)
#   +(V3*((52+$S3)/52))*(1+$T3))*1/$L3
# This is more complex. Let's break it down.
# K = 'Hours per week' (not in this formula)

# Note: The formula in the sheet seems to be calculating the cost per hour, then
# multiplying by hours per week and weeks per year.
# The formula `... * 1/$L3` seems to be dividing by productive time.
# Let's replicate the 'Base Salary + Costs LL'
df["Calculated Base Salary + Costs LL"] = (
    df["Base Salary LL"]
    + (df["Base Salary LL"] * df["Superannuation Rate (%)"])
    + (df["Base Salary LL"] * df["Average Penalties %"])
    + (df["Base Salary LL"] * df["Public Holiday Penalty Percentage"])
    + (df["Base Salary LL"] * df["Private Practice Loading"])
    + (df["Base Salary LL"] * df["Attraction and Retention Allowance"])
    + (df["Base Salary LL"] * df["Sick Leave Percentage"])
    + df["Professional Development Allowance"]
    + (df["Base Salary LL"] * ((52 + df["Annual Leave Entitlement (Weeks)"]) / 52))
    * (1 + df["Annual Leave Loading (%)"])
) * (1 / df["Average productive time (%)"])


# Replicate 'Base Salary + Costs (hourly) LL'
# Formula is =Y3/52/$K3
# Y is 'Base Salary + Costs LL'
# K is 'Hours per week'
df["Calculated Base Salary + Costs (hourly) LL"] = (
    df["Calculated Base Salary + Costs LL"] / 52 / df["Hours per week"]
)


sys.stdout.write("\nData with Calculated Columns:" + "\n")
sys.stdout.write(
    str(
        df[
            [
                "Base Salary LL",
                "Base Salary Mid-point",
                "Calculated Base Salary Mid-point",
                "Base Salary + Costs LL",
                "Calculated Base Salary + Costs LL",
                "Base Salary + Costs (hourly) LL",
                "Calculated Base Salary + Costs (hourly) LL",
            ]
        ].head(),
    )
    + "\n",
)
