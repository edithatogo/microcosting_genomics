"""Prepare labor price and estimate reference tables from Excel workbooks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from unimelb_phd_phase_1.config import load_config


def _parse_generic_sheet(
    file_path: Path | str,
    sheet_name: str,
    header_rows: int,
    skip_rows: int = 0,
) -> pd.DataFrame:
    """Parse a sheet with a fixed number of header rows.

    Parameters
    ----------
    file_path:
        Path to the workbook containing the sheet.
    sheet_name:
        Name of the sheet to parse.
    header_rows:
        Number of header rows before the data begins.
    skip_rows:
        Number of rows to skip before reading the header.
    """
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    header_df = df_raw.iloc[skip_rows : skip_rows + header_rows].copy()
    header_df = header_df.ffill(axis=0)

    columns: list[str] = []
    for i in range(header_df.shape[1]):
        parts = [str(val).strip() for val in header_df.iloc[:, i].values if pd.notna(val)]
        name = " ".join(parts).replace("nan", "").strip()
        name = " ".join(name.split())
        if not name:
            name = f"unnamed_{i}"
        columns.append(name)

    data_df = df_raw.iloc[skip_rows + header_rows :].reset_index(drop=True)
    data_df.columns = columns

    for col in data_df.columns:
        data_df[col] = pd.to_numeric(data_df[col], errors="coerce")

    return data_df


def main() -> None:
    """Create Parquet reference tables used by tests and the calculation engine."""
    config = load_config()
    workbook_key = config.get("default_workbook", "main")
    try:
        workbook_cfg = config["workbooks"][workbook_key]
        source_file = Path(workbook_cfg["path"])
        labor_sheet = workbook_cfg["sheets"]["labor_prices"]
        estimates_sheet = workbook_cfg["sheets"]["estimates"]
    except KeyError as e:
        raise KeyError(
            f"Configuration for workbook '{workbook_key}' is incomplete. Missing key: {e}"
        ) from e

    if not source_file.exists():
        alt_path = config.get("workbooks", {}).get("validation", {}).get("path")
        if alt_path and Path(alt_path).exists():
            source_file = Path(alt_path)

    data_dir = Path(__file__).resolve().parents[1] / "data"
    prepared_dir = data_dir / "prepared"
    prepared_dir.mkdir(exist_ok=True)

    labor_df = _parse_generic_sheet(source_file, labor_sheet, header_rows=2)
    labor_df.to_parquet(prepared_dir / "2._labor_prices.parquet")
    print("Saved 2._labor_prices.parquet")

    estimates_df = _parse_generic_sheet(
        source_file, estimates_sheet, header_rows=3, skip_rows=1
    )
    estimates_df.to_parquet(prepared_dir / "3._estimates.parquet")
    print("Saved 3._estimates.parquet")


if __name__ == "__main__":
    main()
