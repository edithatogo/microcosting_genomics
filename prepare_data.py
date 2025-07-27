"""Prepare cleaned datasets from the microcosting workbooks."""

from pathlib import Path
import pandas as pd
import numpy as np
from unimelb_phd_phase_1.config import load_config

def create_unique_column_names(columns: list[str]) -> list[str]:
    """Ensure column names are unique by appending a suffix if required."""

    seen: dict[str, int] = {}
    unique_columns = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            unique_columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 1
            unique_columns.append(col)
    return unique_columns

def _parse_generic_sheet(
    file_path: Path | str,
    sheet_name: str,
    header_rows: int,
    skip_rows: int = 0,
) -> pd.DataFrame:
    """Parse a sheet with a fixed number of header rows."""

    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    header_df = df_raw.iloc[skip_rows : skip_rows + header_rows].copy()
    header_df = header_df.ffill(axis=0)

    columns: list[str] = []
    for i in range(header_df.shape[1]):
        parts = [
            str(val).strip()
            for val in header_df.iloc[:, i].values
            if pd.notna(val)
        ]
        name = " ".join(parts).replace("nan", "").strip()
        name = " ".join(name.split())
        if not name:
            name = f"unnamed_{i}"
        columns.append(name)

    data_df = df_raw.iloc[skip_rows + header_rows :].reset_index(drop=True)
    data_df.columns = create_unique_column_names(columns)

    for col in data_df.columns:
        data_df[col] = pd.to_numeric(data_df[col], errors="coerce")

    return data_df

def main() -> None:
    """Create cleaned Parquet datasets used for validation."""

    config = load_config()
    workbook_key = config.get("default_workbook", "main")
    try:
        source_file = Path(config["workbooks"][workbook_key]["path"])
        detailed_table_sheet = config["workbooks"][workbook_key]["sheets"]["detailed_table"]
        labor_prices_sheet = config["workbooks"][workbook_key]["sheets"]["labor_prices"]
        estimates_sheet = config["workbooks"][workbook_key]["sheets"]["estimates"]
    except KeyError as e:
        raise KeyError(f"Configuration for workbook '{workbook_key}' is incomplete. Missing key: {e}") from e

    data_dir = Path(__file__).resolve().parents[0] / "data"
    prepared_dir = data_dir / "prepared"
    prepared_dir.mkdir(exist_ok=True)

    # --- 1. Detailed Table -------------------------------------------------
    ground_truth = _parse_generic_sheet(source_file, detailed_table_sheet, header_rows=3)
    ground_truth.to_parquet(prepared_dir / "ground_truth.parquet")
    print("Saved ground_truth.parquet")

    # --- 2. Labor Prices & 3. Estimates -----------------------------------
    labor_prices = _parse_generic_sheet(source_file, labor_prices_sheet, header_rows=2)
    labor_prices.to_parquet(prepared_dir / "2._labor_prices.parquet")
    print("Saved 2._labor_prices.parquet")

    estimates = _parse_generic_sheet(source_file, estimates_sheet, header_rows=3, skip_rows=1)
    estimates.to_parquet(prepared_dir / "3._estimates.parquet")
    print("Saved 3._estimates.parquet")


if __name__ == "__main__":
    main()

