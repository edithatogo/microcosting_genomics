import json
import sys


def clean_notebook(input_path, output_path):
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {input_path}: {e}", file=sys.stderr)
        # Try to read the file line by line and fix it
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()
        # This is a simplistic way to fix some common JSON errors, like trailing commas
        # A more robust solution might be needed if this fails
        import re

        content = re.sub(r",\s*([\}\]])", r"\1", content)
        try:
            notebook = json.loads(content)
        except json.JSONDecodeError as e2:
            print(
                f"Failed to fix and decode JSON from {input_path}: {e2}",
                file=sys.stderr,
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

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=1)


if __name__ == "__main__":
    clean_notebook(
        "/Users/doughnut/GitHub/microcosting_genomics/notebooks/Microcosting Study.ipynb",
        "/Users/doughnut/GitHub/microcosting_genomics/notebooks/Microcosting Study.ipynb",
    )
    clean_notebook(
        "/Users/doughnut/GitHub/microcosting_genomics/notebooks/Microcosting_Analysis.ipynb",
        "/Users/doughnut/GitHub/microcosting_genomics/notebooks/Microcosting_Analysis.ipynb",
    )
