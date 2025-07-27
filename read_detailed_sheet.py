"""Convert the detailed table sheet to a long-format Parquet file."""

from pathlib import Path
import pandas as pd

from unimelb_phd_phase_1.config import load_config

DATA_DIR = Path(__file__).resolve().parents[0] / "data"


def main() -> None:
    config = load_config()
    workbook_key = config.get("default_workbook", "main")
    try:
        file_path = Path(config["workbooks"][workbook_key]["path"])
        sheet_name = config["workbooks"][workbook_key]["sheets"]["detailed_table"]
    except KeyError as e:
        raise KeyError(
            f"Configuration for workbook '{workbook_key}' is incomplete. Missing key: {e}"
        ) from e

    df = pd.read_excel(file_path, sheet_name=sheet_name, header=[0, 1, 2, 3])

    df.columns = [
        " ".join(str(p).strip() for p in col if pd.notna(p)) for col in df.columns
    ]

    id_vars = [c for c in df.columns if c.lower().startswith("unnamed")]
    df_long = df.melt(id_vars=id_vars, var_name="variable", value_name="value")
    df_long["value"] = df_long["value"].astype(str)

    df_long.to_parquet(DATA_DIR / "detailed_table.parquet")
    print("Successfully converted the detailed table to a long format parquet file.")


if __name__ == "__main__":
    main()
