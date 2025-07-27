"""Append a code cell to the Microcosting analysis notebook.

The notebook is expected to reside in the ``notebooks`` directory at
``Path(__file__).resolve().parents[0] / 'notebooks'`` and uses data from the
repository ``data`` directory.
"""

from pathlib import Path
import json

NOTEBOOK_DIR = Path(__file__).resolve().parents[0] / 'notebooks'
DATA_DIR = Path(__file__).resolve().parents[0] / 'data'
notebook_path = NOTEBOOK_DIR / 'Microcosting_Analysis.ipynb'

with open(notebook_path, 'r') as f:
    notebook = json.load(f)

new_cell = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "import numpy as np\n",
        "import scipy.stats as stats\n",
        "import pandas as pd\n",
        "\n",
        "# Read the cleaned data\n",
        "from pathlib import Path\n",
        "data_dir = Path(__file__).resolve().parents[1] / 'data'\n",
        "df = pd.read_csv(data_dir / 'cleaned_detailed_table.csv')\n",
        "\n",
        "# Get the unit cost columns\n",
        "unit_cost_cols = [col for col in df.columns if 'Unit Cost' in col]\n",
        "\n",
        "# Extract the unit cost data\n",
        "unit_cost_data = df[unit_cost_cols].values.flatten()\n",
        "\n",
        "# Remove NaN values\n",
        "unit_cost_data = unit_cost_data[~np.isnan(unit_cost_data)]\n",
        "\n",
        "# Fit a gamma distribution to the data\n",
        "shape, loc, scale = stats.gamma.fit(unit_cost_data, floc=0)\n",
        "\n",
        "# Perform Monte Carlo simulation\n",
        "n_simulations = 10000\n",
        "simulations = np.random.gamma(shape, scale=scale, size=n_simulations)\n",
        "\n",
        "# Calculate the 2.5th, 50th, and 97.5th centiles\n",
        "centiles = np.percentile(simulations, [2.5, 50, 97.5])\n",
        "\n",
        "# Print the results\n",
        "print(f'Gamma Distribution Parameters: shape={shape}, scale={scale}')\n",
        "print(f'Centiles: 2.5th={centiles[0]}, 50th={centiles[1]}, 97.5th={centiles[2]}')\n"
    ]
}

notebook['cells'].append(new_cell)

with open(notebook_path, 'w') as f:
    json.dump(notebook, f, indent=1)
