# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Read Excel header hierarchies into uniquely named Polars columns."""

lazy from collections.abc import Sequence
lazy from pathlib import Path

import openpyxl
import polars as pl


def _number(value: object) -> float | None:
    """Coerce numeric Excel input while preserving unparseable values as null."""
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def load_sheet_with_headers(
    file_path: str | Path,
    sheet_name: str,
    *,
    header_rows: int,
    string_columns: Sequence[str] | None = None,
) -> pl.DataFrame:
    """Expand merged cells and preserve all header levels in flat column names.

    Declared text columns retain text; other columns use nullable Float64.
    Source files are never modified. Header counts are explicit source metadata.
    """
    if header_rows < 1:
        message = "At least one header row is required"
        raise ValueError(message)
    workbook = openpyxl.load_workbook(file_path, data_only=True)
    try:
        sheet = workbook[sheet_name]
        merged: dict[tuple[int, int], object] = {}
        for region in sheet.merged_cells.ranges:
            left, top, right, bottom = region.bounds
            value = sheet.cell(top, left).value
            for row in range(top, bottom + 1):
                for column in range(left, right + 1):
                    merged[row, column] = value
        rows: list[list[object]] = [
            [merged.get((r, c), cell.value) for c, cell in enumerate(row, 1)]
            for r, row in enumerate(sheet.iter_rows(), 1)
        ]
    finally:
        workbook.close()
    if header_rows > len(rows):
        message = "Header rows exceed worksheet length"
        raise ValueError(message)
    columns: list[pl.Series] = []
    used: set[str] = set()
    text_labels = set(string_columns or ())
    for index in range(len(rows[0])):
        labels = list(
            dict.fromkeys(
                str(row[index]) for row in rows[:header_rows] if row[index] is not None
            ),
        )
        base = " ".join(labels) or f"unnamed_{index}"
        name = base
        suffix = 1
        while name in used:
            suffix += 1
            name = f"{base}_{suffix}"
        used.add(name)
        values = [row[index] for row in rows[header_rows:]]
        if text_labels.intersection(labels):
            columns.append(
                pl.Series(
                    name,
                    [str(v) if v is not None else None for v in values],
                    dtype=pl.String,
                ),
            )
        else:
            columns.append(
                pl.Series(name, [_number(v) for v in values], dtype=pl.Float64),
            )
    return pl.DataFrame(columns)
