# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Remove incomplete cells and repair malformed notebook JSON."""

import json
import re
import sys
from pathlib import Path


def clean_notebook(input_path: str | Path, output_path: str | Path) -> None:
    """Repair notebook JSON and remove incomplete code cells."""
    try:
        with Path(input_path).open(encoding="utf-8") as f:
            notebook = json.load(f)
    except json.JSONDecodeError as e:
        sys.stderr.writelines((f"Error decoding JSON from {input_path}: {e}", "\n"))
        # Try to read the file line by line and fix it
        with Path(input_path).open(encoding="utf-8") as f:
            content = f.read()
        # This is a simplistic way to fix some common JSON errors, like trailing commas
        # A more robust solution might be needed if this fails

        content = re.sub(r",\s*([\}\]])", r"\1", content)
        try:
            notebook = json.loads(content)
        except json.JSONDecodeError as e2:
            sys.stderr.writelines(
                (f"Failed to fix and decode JSON from {input_path}: {e2}", "\n"),
            )
            sys.exit(1)

    good_cells = []
    for cell in notebook.get("cells", []):
        is_bad = False
        if "source" in cell and isinstance(cell.get("source"), list):
            for line in cell["source"]:
                if "Apologies, it seems like the response got cut off" in line:
                    is_bad = True
                    break
        if not is_bad:
            good_cells.append(cell)

    notebook["cells"] = good_cells

    with Path(output_path).open("w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=1)


if __name__ == "__main__":
    clean_notebook(
        (
            "/Users/doughnut/GitHub/microcosting_genomics/notebooks/Microcosting"
            " Study.ipynb"
        ),
        (
            "/Users/doughnut/GitHub/microcosting_genomics/notebooks/Microcosting"
            " Study.ipynb"
        ),
    )
    clean_notebook(
        "/Users/doughnut/GitHub/microcosting_genomics/notebooks/Microcosting_Analysis.ipynb",
        "/Users/doughnut/GitHub/microcosting_genomics/notebooks/Microcosting_Analysis.ipynb",
    )
