from pathlib import Path
import pandas as pd
from unimelb_phd_phase_1.config import load_config

def _parse_generic_sheet(file_path: Path | str, sheet_name: str, header_rows: int, skip_rows: int = 0) -> pd.DataFrame:
    df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    header_df = df_raw.iloc[skip_rows : skip_rows + header_rows].ffill(axis=0)

    columns: list[str] = []
    for i in range(header_df.shape[1]):
        parts = [str(v).strip() for v in header_df.iloc[:, i].values if pd.notna(v)]
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
    config = load_config()
    workbook_key = config.get("default_workbook", "main")
    workbook = config["workbooks"][workbook_key]
    excel_path = Path(workbook["path"])
    sheets = workbook["sheets"]

    prepared_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
    prepared_dir.mkdir(exist_ok=True)

    labor_df = _parse_generic_sheet(excel_path, sheets["labor_prices"], header_rows=2)
    labor_df.to_parquet(prepared_dir / "2._labor_prices.parquet")
    print("Saved 2._labor_prices.parquet")

    estimates_df = _parse_generic_sheet(excel_path, sheets["estimates"], header_rows=3, skip_rows=1)
    estimates_df.to_parquet(prepared_dir / "3._estimates.parquet")
    print("Saved 3._estimates.parquet")

if __name__ == "__main__":
    main()
