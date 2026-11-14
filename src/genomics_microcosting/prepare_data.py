# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Prepare cleaned datasets from the microcosting workbooks."""

import logging
import os
from pathlib import Path

import polars as pl
from openpyxl import load_workbook

from genomics_microcosting.config import load_config

logger = logging.getLogger(__name__)


def create_unique_column_names(columns: list[str]) -> list[str]:
    """Ensure column names are unique by appending a suffix if required."""
    seen: dict[str, int] = {}
    unique_columns: list[str] = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            unique_columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 1
            unique_columns.append(col)
    return unique_columns


def parse_reference_sheet(
    file_path: Path | str,
    sheet_name: str,
    header_rows: int,
    skip_rows: int = 0,
) -> pl.DataFrame:
    """Parse fixed worksheet headers and preserve calculated values."""
    wb = load_workbook(file_path, read_only=True, data_only=True)
    try:
        rows = iter(wb[sheet_name].values)
        for _ in range(skip_rows):
            next(rows)
        header = [next(rows) for _ in range(header_rows)]
        names: list[str] = []
        for i, parts in enumerate(zip(*header, strict=True)):
            label = " ".join(
                dict.fromkeys(str(p).strip() for p in parts if p is not None),
            )
            names.append(" ".join(label.split()) or f"unnamed_{i}")
        names = create_unique_column_names(names)
        frame = pl.DataFrame(
            [[str(v) if v is not None else None for v in row] for row in rows],
            schema=dict.fromkeys(names, pl.String),
            orient="row",
            strict=False,
        )
        identifiers = {"test", "category", "stage", "sub_category", "step", "source"}
        return frame.with_columns(
            pl.col(n).cast(pl.Float64, strict=False)
            for n in names
            if n.lower() not in identifiers
        )
    finally:
        wb.close()


# Keep existing callers compatible while helper scripts use the public boundary.
_parse_generic_sheet = parse_reference_sheet


def main() -> None:
    """Create cleaned Parquet datasets used for validation."""
    config = load_config()
    workbook_key = config.get("default_workbook", "main")
    workbook_config = config.get("workbooks", {}).get(workbook_key, {})
    path = workbook_config.get("path")
    sheet_configs = workbook_config.get("sheets")
    if path is None or sheet_configs is None:
        key = "path" if path is None else "sheets"
        message = f"Configuration for workbook '{workbook_key}' is missing {key}"
        raise KeyError(message)
    source_file = Path(path)

    # Load workbook to check available sheets
    workbook = load_workbook(filename=source_file, data_only=True, read_only=True)
    try:
        sheet_names = set(workbook.sheetnames)
    finally:
        workbook.close()

    data_dir = Path(__file__).resolve().parents[2] / "data"
    prepared_dir = Path(
        os.environ.get("MICROCOSTING_OUTPUT_DIR", data_dir / "prepared"),
    )
    prepared_dir.mkdir(parents=True, exist_ok=True)

    # Process configured sheets
    processed_sheets: set[str] = set()
    for sheet_name, sheet_config in sheet_configs.items():
        # Skip sheets that don't exist in the workbook
        if sheet_name not in sheet_names:
            logger.info(
                "%s",
                f"Warning: Sheet '{sheet_name}' not found in workbook, skipping",
            )
            continue

        df = _parse_generic_sheet(
            source_file,
            sheet_name,
            header_rows=sheet_config.get("header_rows", 1),
            skip_rows=sheet_config.get("skip_rows", 0),
        )

        # Use a sanitized version of the sheet name for the file name
        sanitized_name = "".join(
            c for c in sheet_name if c.isalnum() or c in (" ", "_")
        ).rstrip()
        sanitized_name = sanitized_name.lower().replace(" ", "_")

        # Save as Parquet
        output_path = prepared_dir / f"{sanitized_name}.parquet"
        df.write_parquet(output_path)
        logger.info("%s", f"Saved {output_path}")

        # Save as CSV
        csv_output_path = prepared_dir / f"{sanitized_name}.csv"
        df.write_csv(csv_output_path)
        logger.info("%s", f"Saved {csv_output_path}")

        processed_sheets.add(sheet_name)

    # Process additional supporting tables not in config
    supporting_tables = [
        "Summary Table",
        "DSA - Summary",
        "DSA - Tornado (index 0)",
        "DSA - Tornado (index actual)",
        "DSA - Tornado Actual",
        "DSA - Differences",
        "DSA - Summary (2)",
        "DSA - Summary - Stats",
        "Process",
        "DSA - Overheads",
        "DSA - Overheads (USD)",
        "DSA - Consumable Discounts",
        "DSA - Cons Discounts (USD)",
        "Process - WES+Panel - VCGS",
        "Process - WGS - VCGS",
        "At a Glance",
        "Summary 20230812",
        "Summ Tab by Cat",
        "Summ Tab by Stage",
        "Summ Table for Graph",
        "Summary Table 2",
        "Summary Table Ordered",
        "Sheet1",
        "Sheet2",
    ]

    logger.info(
        "%s",
        f"\nProcessing {len(supporting_tables)} additional supporting tables...",
    )

    for sheet_name in supporting_tables:
        if sheet_name in sheet_names and sheet_name not in processed_sheets:
            try:
                # Try to auto-detect header structure
                df = _parse_generic_sheet(
                    source_file,
                    sheet_name,
                    header_rows=1,  # Default to 1 header row for supporting tables
                    skip_rows=0,
                )

                # Use a sanitized version of the sheet name for the file name
                sanitized_name = "".join(
                    c
                    for c in sheet_name
                    if c.isalnum() or c in (" ", "_", "-", "(", ")")
                ).rstrip()
                sanitized_name = (
                    sanitized_name.lower()
                    .replace(" ", "_")
                    .replace("-", "_")
                    .replace("(", "")
                    .replace(")", "")
                )

                # Save as Parquet
                output_path = prepared_dir / f"{sanitized_name}.parquet"
                df.write_parquet(output_path)
                logger.info("%s", f"Saved supporting table: {output_path}")

                # Save as CSV
                csv_output_path = prepared_dir / f"{sanitized_name}.csv"
                df.write_csv(csv_output_path)
                logger.info("%s", f"Saved supporting table: {csv_output_path}")

            except (OSError, ValueError, StopIteration, pl.exceptions.PolarsError) as e:
                logger.info(
                    "%s",
                    f"Warning: Could not process supporting table '{sheet_name}': {e}",
                )

    logger.info(
        "%s",
        (
            f"\nData preparation complete. Processed {len(processed_sheets)} "
            f"configured sheets and additional supporting tables."
        ),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
