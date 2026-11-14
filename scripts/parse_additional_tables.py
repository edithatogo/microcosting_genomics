# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Parse supplemental Excel tables and save them as Parquet files."""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl
from openpyxl import load_workbook

from genomics_microcosting.config import load_config
from genomics_microcosting.prepare_data import parse_reference_sheet


def _read_flat_sheet(path: Path, sheet_name: str, header_index: int) -> pl.DataFrame:
    """Read cached source cells with an explicit header offset and no rewrites."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = list(workbook[sheet_name].values)
    finally:
        workbook.close()
    while rows and all(value is None for value in rows[-1]):
        rows.pop()
    width = len(rows[header_index])
    while width and all(row[width - 1] is None for row in rows[header_index:]):
        width -= 1
    rows = [row[:width] for row in rows]
    header = rows[header_index]
    columns = [
        str(value) if value is not None else f"Unnamed: {i}"
        for i, value in enumerate(header)
    ]
    values = rows[header_index + 1 :]
    return pl.DataFrame(values, schema=columns, orient="row", strict=False)


def _get_workbook_path() -> Path:
    cfg = load_config()
    key = cfg.get("default_workbook", "main")
    path = Path(cfg["workbooks"][key]["path"])
    if not path.exists():
        alt = cfg.get("workbooks", {}).get("validation", {}).get("path")
        if alt and Path(alt).exists():
            path = Path(alt)
    return path


def parse_dsa_equipment_throughput(path: Path) -> pl.DataFrame:
    """Read equipment throughput assumptions for sensitivity analysis."""
    return parse_reference_sheet(path, "DSA - Test Throughput", 4)


def parse_dsa_overheads(path: Path) -> pl.DataFrame:
    """Read overhead rates for sensitivity analysis."""
    return parse_reference_sheet(path, "DSA - Overheads", 4)


def parse_dsa_consumable_discounts(path: Path) -> pl.DataFrame:
    """Read consumable discounts for sensitivity analysis."""
    return parse_reference_sheet(path, "DSA - Consumable Discounts", 4)


def parse_dsa_labour_prices(path: Path) -> pl.DataFrame:
    """Read labour prices for sensitivity analysis."""
    return parse_reference_sheet(path, "DSA - Labour Prices", 4)


def parse_summary_table(path: Path) -> pl.DataFrame:
    """Read the workbook's cost summary."""
    return parse_reference_sheet(path, "Summary Table", 4)


def parse_process_table(path: Path) -> pl.DataFrame:
    """Read process steps from the first header row."""
    return _read_flat_sheet(path, "Process", 0)


def parse_at_a_glance(path: Path) -> pl.DataFrame:
    """Read the workbook overview beneath its title row."""
    return _read_flat_sheet(path, "At a Glance", 1)


def parse_psa_table(csv_path: Path) -> pl.DataFrame:
    """Read probabilistic sensitivity inputs with string identifiers."""
    return pl.read_csv(
        csv_path,
        schema_overrides={"Test": pl.String, "Category": pl.String, "Stage": pl.String},
    )


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
    """Convert supplemental workbook tables and any available PSA CSV."""
    source_file = _get_workbook_path()
    data_dir = Path(__file__).resolve().parents[1] / "data"
    prepared_dir = data_dir / "prepared"
    prepared_dir.mkdir(exist_ok=True)

    for name, parser in PARSERS.items():
        if name == "psa.parquet":
            continue
        df = parser(source_file)
        df.write_parquet(prepared_dir / name)
        sys.stdout.write(f"Saved {name}\n")

    # PSA table uses a separate CSV file
    psa_csv = (
        data_dir
        / "Microcosting - Study 1 - Utilisation and Microcosts v14 (20230814) PSA.csv"
    )
    if psa_csv.exists():
        df_psa = parse_psa_table(psa_csv)
        df_psa.write_parquet(prepared_dir / "psa.parquet")
        sys.stdout.write("Saved psa.parquet\n")


if __name__ == "__main__":
    main()
