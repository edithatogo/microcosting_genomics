# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Parse cost-related tables and save them as Parquet files."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import polars as pl

from genomics_microcosting.prepare_data import create_unique_column_names


def _parse_generic_csv(path: Path | str, header_rows: int) -> pl.DataFrame:
    """Parse a CSV file that contains multiple header rows."""
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        rows = [
            row
            for row in csv.reader(stream)
            if row and not (len(row) == 1 and not row[0].strip())
        ]
    if not rows:
        message = "Source CSV has no header rows"
        raise ValueError(message)
    width = len(rows[0])
    if any(len(row) > width for row in rows):
        message = "Source CSV contains an inconsistent row width"
        raise ValueError(message)
    padded = [row + [""] * (width - len(row)) for row in rows]
    columns: list[str] = []
    missing_labels = {"", "NA", "N/A", "NaN", "nan", "NULL", "null", "None"}
    for column in range(width):
        last: str | None = None
        parts: list[str] = []
        for row in padded[:header_rows]:
            value = row[column].strip()
            if value not in missing_labels:
                last = value
            if last is not None:
                parts.append(last)
        name = " ".join(" ".join(parts).replace("nan", "").split())
        columns.append(name or f"unnamed_{column}")
    names = create_unique_column_names(columns)
    series: list[pl.Series] = []
    for column, name in enumerate(names):
        values: list[float | None] = []
        for row in padded[header_rows:]:
            try:
                values.append(float(row[column]))
            except ValueError:
                values.append(None)
        series.append(pl.Series(name, values, dtype=pl.Float64))
    return pl.DataFrame(series)


def parse_equipment_costs(path: Path) -> pl.DataFrame:
    """Parse the equipment costs table."""
    return _parse_generic_csv(path, header_rows=4)


def parse_consumable_costs(path: Path) -> pl.DataFrame:
    """Parse the consumable costs table."""
    return _parse_generic_csv(path, header_rows=3)


def parse_labour_costs(path: Path) -> pl.DataFrame:
    """Parse the labour costs table."""
    return _parse_generic_csv(path, header_rows=2)


def main() -> None:
    """Convert the three source cost tables to Parquet."""
    data_dir = Path(__file__).resolve().parents[1] / "data"
    prepared_dir = data_dir / "prepared"
    prepared_dir.mkdir(exist_ok=True)

    parsers = {
        "equipment_costs.parquet": (
            parse_equipment_costs,
            data_dir / "Eq - Costs and Usage - VCGS.csv",
        ),
        "consumable_costs.parquet": (
            parse_consumable_costs,
            data_dir / "Cons -  Costs and Util - VCGS.csv",
        ),
        "labour_costs.parquet": (
            parse_labour_costs,
            data_dir / "Labour - Costs - VCGS.csv",
        ),
    }

    for name, (parser, path) in parsers.items():
        df = parser(path)
        df.write_parquet(prepared_dir / name)
        sys.stdout.write(f"Saved {name}\n")


if __name__ == "__main__":
    main()
