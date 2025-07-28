"""Parse supplemental Excel tables and save them as Parquet files."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

from prepare_data import _parse_generic_sheet
from unimelb_phd_phase_1.config import load_config


def _get_workbook_path() -> Path:
    cfg = load_config()
    key = cfg.get("default_workbook", "main")
    path = Path(cfg["workbooks"][key]["path"])
    if not path.exists():
        alt = cfg.get("workbooks", {}).get("validation", {}).get("path")
        if alt and Path(alt).exists():
            path = Path(alt)
    return path


def parse_dsa_equipment_throughput(path: Path) -> pd.DataFrame:
    return _parse_generic_sheet(path, "DSA - Test Throughput", 4)


def parse_dsa_overheads(path: Path) -> pd.DataFrame:
    return _parse_generic_sheet(path, "DSA - Overheads", 4)


def parse_dsa_consumable_discounts(path: Path) -> pd.DataFrame:
    return _parse_generic_sheet(path, "DSA - Consumable Discounts", 4)


def parse_dsa_labour_prices(path: Path) -> pd.DataFrame:
    return _parse_generic_sheet(path, "DSA - Labour Prices", 4)


def parse_summary_table(path: Path) -> pd.DataFrame:
    return _parse_generic_sheet(path, "Summary Table", 4)


def parse_process_table(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Process")
    return df


def parse_at_a_glance(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="At a Glance", header=1)
    return df


def parse_psa_table(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return df


PARSERS = {
    "4._dsa_equipment_throughput.parquet": parse_dsa_equipment_throughput,
    "5._dsa_overheads.parquet": parse_dsa_overheads,
    "6._dsa_consumable_discounts.parquet": parse_dsa_consumable_discounts,
    "7._dsa_labour_prices.parquet": parse_dsa_labour_prices,
    "summary_table.parquet": parse_summary_table,
    "process.parquet": parse_process_table,
    "at_a_glance.parquet": parse_at_a_glance,
}


def main() -> None:
    source_file = _get_workbook_path()
    data_dir = Path(__file__).resolve().parents[1] / "data"
    prepared_dir = data_dir / "prepared"
    prepared_dir.mkdir(exist_ok=True)

    for name, parser in PARSERS.items():
        if name == "psa.parquet":
            continue
        df = parser(source_file)
        df.to_parquet(prepared_dir / name)
        print(f"Saved {name}")

    # PSA table uses a separate CSV file
    psa_csv = data_dir / "Microcosting - Study 1 - Utilisation and Microcosts v14 (20230814) PSA.csv"
    if psa_csv.exists():
        df_psa = parse_psa_table(psa_csv)
        df_psa.to_parquet(prepared_dir / "psa.parquet")
        print("Saved psa.parquet")


if __name__ == "__main__":
    main()
