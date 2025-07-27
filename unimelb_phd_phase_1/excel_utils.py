from __future__ import annotations

from pathlib import Path
from typing import Sequence

import openpyxl
import pandas as pd


def load_sheet_with_headers(
    file_path: str | Path,
    sheet_name: str,
    *,
    header_rows: int,
    string_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Read an Excel sheet with multiple header rows.

    Merged cells are expanded and header rows are forward filled. Columns
    listed in ``string_columns`` are left as object type while all others
    are coerced to numeric where possible.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb[sheet_name]

    # Build a lookup for merged cell values so we can expand them
    merged_lookup: dict[tuple[int, int], object] = {}
    for merged_range in ws.merged_cells.ranges:
        min_row, min_col, max_row, max_col = merged_range.bounds
        value = ws.cell(row=min_row, column=min_col).value
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                merged_lookup[(r, c)] = value

    raw_rows = []
    for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        row_vals = []
        for c_idx, val in enumerate(row, start=1):
            if val is None and (r_idx, c_idx) in merged_lookup:
                val = merged_lookup[(r_idx, c_idx)]
            row_vals.append(val)
        raw_rows.append(row_vals)

    df = pd.DataFrame(raw_rows)
    header_df = df.iloc[:header_rows].ffill(axis=0)
    data_df = df.iloc[header_rows:].copy()
    data_df.columns = pd.MultiIndex.from_arrays(header_df.values)
    data_df.reset_index(drop=True, inplace=True)

    if string_columns is None:
        string_columns = []
    converted_cols = []
    for idx, col in enumerate(data_df.columns):
        label = col[1] if isinstance(col, tuple) else col
        series = data_df.iloc[:, idx]
        if label not in string_columns:
            series = pd.to_numeric(series, errors="coerce")
        converted_cols.append(series)

    data_df = pd.concat(converted_cols, axis=1)
    data_df.columns = pd.MultiIndex.from_arrays(header_df.values)
    return data_df
