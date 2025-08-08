"""Run basic analysis on the microcosting detailed table."""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as stats


# Function to extract the last number from a string, returning NaN if not found
def extract_last_number(s):
    if isinstance(s, str):
        # This regex finds numbers, including decimals
        numbers = re.findall(r"[-+]?\d*\.?\d+", s)
        if numbers:
            return float(numbers[-1])
    # Check if the value is already numeric
    if isinstance(s, (int, float)):
        return s
    return np.nan


# Load the data, skipping the first row and using the next two as headers
DATA_DIR = Path(__file__).resolve().parents[0] / "data"
df = pd.read_csv(DATA_DIR / "Detailed Table.csv", header=[1, 2], skiprows=[0])

# Select columns that contain 'Unit Cost' in the top-level header
unit_cost_cols = [col for col in df.columns if "Unit Cost" in col[0]]
unit_cost_df = df[unit_cost_cols]

# Apply the cleaning function to the selected data
cleaned_unit_cost_df = unit_cost_df.applymap(extract_last_number)

# Flatten the DataFrame to a single series and drop NaN values
unit_cost_data = cleaned_unit_cost_df.values.flatten()
unit_cost_data = unit_cost_data[~np.isnan(unit_cost_data)]

# Ensure we have data to fit
if unit_cost_data.size > 0:
    # Fit a gamma distribution to the data
    shape, loc, scale = stats.gamma.fit(
        unit_cost_data, floc=0
    )  # floc=0 to fix location at 0

    # Perform Monte Carlo simulation
    n_simulations = 10000
    simulations = stats.gamma.rvs(shape, loc=loc, scale=scale, size=n_simulations)

    # Calculate the 2.5th, 50th, and 97.5th centiles
    centiles = np.percentile(simulations, [2.5, 50, 97.5])

    print("Successfully fitted Gamma Distribution.")
    print(f"Parameters: shape={shape:.4f}, loc={loc:.4f}, scale={scale:.4f}")
    print(
        f"Centiles: 2.5th={centiles[0]:.4f}, 50th={centiles[1]:.4f}, 97.5th={centiles[2]:.4f}"
    )
else:
    print("No valid unit cost data found to perform analysis.")
