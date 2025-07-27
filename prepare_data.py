"""Prepare cleaned datasets from the microcosting workbooks."""

from pathlib import Path
import pandas as pd

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

    data_dir = Path(__file__).resolve().parents[0] / "data"

    # --- 1. Detailed Table -------------------------------------------------
    main_wb = data_dir / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    ground_truth = _parse_generic_sheet(main_wb, "Detailed Table", header_rows=3)
    (data_dir / "prepared").mkdir(exist_ok=True)
    ground_truth.to_parquet(data_dir / "prepared" / "ground_truth.parquet")
    print("Saved ground_truth.parquet")

    # --- 2. Labor Prices & 3. Estimates -----------------------------------
    supp_wb = data_dir / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"

    labor_prices = _parse_generic_sheet(supp_wb, "2. Labor Prices", header_rows=2)
    labor_prices.to_parquet(data_dir / "prepared" / "2._labor_prices.parquet")
    print("Saved 2._labor_prices.parquet")

    estimates = _parse_generic_sheet(supp_wb, "3. Estimates", header_rows=3, skip_rows=1)
    estimates.to_parquet(data_dir / "prepared" / "3._estimates.parquet")
    print("Saved 3._estimates.parquet")


if __name__ == "__main__":
    main()

