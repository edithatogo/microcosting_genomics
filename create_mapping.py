# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Create a step to label mapping CSV.

Data files are stored in the repository ``data`` directory located at
``Path(__file__).resolve().parents[0] / 'data'``.
"""

import sys
from pathlib import Path

import pandas as pd

# Create a dictionary with the mappings
mapping = {
    "Step": [
        "Registration",
        "Name Check",
        "Completion of forms",
        "Unpacking/Triaging ",
        "Rapid Registration of the sample ",
        "Data Entry / Data Review ",
        "Venepuncture",
        "Referrer Liaison - MS",
        "gDNA Extraction Kit - Labwork",
        "gDNA QC - Labwork",
        "Bioinformatics pipeline maintenance and development",
        "Case Setup",
        "Case QC",
    ],
    "Label": [
        "AS",
        "AS",
        "AS",
        "AS",
        "AS",
        "AS",
        "LT",
        "MS",
        "LT",
        "LT",
        "BI",
        "BI",
        "BI",
    ],
}

# Create a dataframe from the dictionary
df_mapping = pd.DataFrame(mapping)

# Save the mapping to a CSV file
DATA_DIR = Path(__file__).resolve().parents[0] / "data"
mapping_file_path = DATA_DIR / "step_to_label_mapping.csv"
df_mapping.to_csv(mapping_file_path, index=False)

sys.stdout.writelines((f"Mapping saved to {mapping_file_path}", "\n"))
