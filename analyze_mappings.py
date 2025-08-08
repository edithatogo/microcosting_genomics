"""Analyze mappings between steps and labels.

Data files are expected in the repository ``data`` directory located at
``Path(__file__).resolve().parents[0] / 'data'``.
"""

from pathlib import Path

import pandas as pd

# Load the Detailed Table data
DATA_DIR = Path(__file__).resolve().parents[0] / "data" / "extracted"
df_detailed = pd.read_csv(DATA_DIR / "Detailed Table_values.csv", header=2)
df_detailed.dropna(how="all", inplace=True)
df_detailed.reset_index(drop=True)

# Load the Labour Costs data
df_labour = pd.read_csv(DATA_DIR / "Labour - Costs - VCGS_values.csv", header=1)
df_labour.dropna(how="all", inplace=True)
df_labour.reset_index(drop=True)

# Clean up column names
detailed_columns = [
    "Test",
    "Category",
    "Sub-Category",
    "Step",
    "Quantity LL",
    "Quantity Estimate",
    "Quantity UL",
    "Quantity Source",
    "Price LL",
    "Price Estimate",
    "Price UL",
    "Price Source",
    "Unit Cost LL",
    "Unit Cost Estimate",
    "Unit Cost UL",
    "DSA Price LL",
    "DSA Price Estimate",
    "DSA Price UL",
    "DSA Unit Cost LL",
    "DSA Unit Cost Estimate",
    "DSA Unit Cost UL",
    "VIC Cost LL",
    "VIC Cost Estimate",
    "VIC Cost UL",
    "SA Cost LL",
    "SA Cost Estimate",
    "SA Cost UL",
]
df_detailed.columns = detailed_columns[: len(df_detailed.columns)]

labour_columns = [
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
df_labour.columns = labour_columns


# Get unique values
detailed_steps = df_detailed["Step"].unique()
labour_labels = df_labour["Label"].unique()

print("Unique Steps in Detailed Table:")
for step in detailed_steps:
    print(f"- {step}")

print("\nUnique Labels in Labour Costs:")
for label in labour_labels:
    print(f"- {label}")
