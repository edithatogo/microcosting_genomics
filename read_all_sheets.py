"""Load all sheets from the configured workbook."""

from pathlib import Path
import pandas as pd

from unimelb_phd_phase_1.config import load_config

DATA_DIR = Path(__file__).resolve().parents[0] / "data"


def main() -> None:
    config = load_config()
    workbook_key = config.get("default_workbook", "main")
    try:
        file_path = Path(config["workbooks"][workbook_key]["path"])
    except KeyError as e:
        raise KeyError(
            f"Configuration for workbook '{workbook_key}' is incomplete. Missing key: {e}"
        ) from e

    dfs = pd.read_excel(file_path, sheet_name=None)
    print(dfs.keys())


if __name__ == "__main__":
    main()
