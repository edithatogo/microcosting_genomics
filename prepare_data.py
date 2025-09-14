"""Prepare cleaned datasets from the microcosting workbooks."""

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from genomics_microcosting.config import load_config


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
    """Parse a sheet with a fixed number of header rows, preserving calculated values."""

    # Load workbook with data_only=True to get calculated values instead of formulas
    wb = load_workbook(filename=file_path, data_only=True)
    ws = wb[sheet_name]

    # Convert to DataFrame
    data = []
    for row in ws.iter_rows(values_only=True):
        data.append(row)

    df_raw = pd.DataFrame(data)

    # Process headers
    header_df = df_raw.iloc[skip_rows : skip_rows + header_rows].copy()
    header_df = header_df.ffill(axis=0)

    columns: list[str] = []
    for i in range(header_df.shape[1]):
        parts = [
            str(val).strip() for val in header_df.iloc[:, i].values if pd.notna(val)
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_parts = []
        for part in parts:
            if part not in seen:
                unique_parts.append(part)
                seen.add(part)

        name = " ".join(unique_parts).replace("nan", "").strip()
        name = " ".join(name.split())  # Normalize whitespace

        if not name:
            name = f"unnamed_{i}"
        columns.append(name)

    data_df = df_raw.iloc[skip_rows + header_rows :].reset_index(drop=True)
    data_df.columns = create_unique_column_names(columns)

    # Apply type conversion with better error handling
    for col in data_df.columns:
        # Try to preserve string columns as specified in config
        if col.lower() in ['test', 'category', 'sub_category', 'step', 'source']:
            # Keep as string if it contains non-numeric data
            try:
                # Check if column contains only NaN or numeric values that could be strings
                if data_df[col].notna().any():
                    # If it looks like it should be string, keep it as object
                    sample_values = data_df[col].dropna().head(10)
                    if any(isinstance(val, str) or pd.isna(val) for val in sample_values):
                        continue  # Keep as object/string
            except:
                pass

        # Apply numeric conversion
        data_df[col] = pd.to_numeric(data_df[col], errors="coerce")

    return data_df


def main() -> None:
    """Create cleaned Parquet datasets used for validation."""

    config = load_config()
    workbook_key = config.get("default_workbook", "main")
    try:
        source_file = Path(config["workbooks"][workbook_key]["path"])
        sheet_configs = config["workbooks"][workbook_key]["sheets"]
    except KeyError as e:
        raise KeyError(
            f"Configuration for workbook '{workbook_key}' is incomplete. Missing key: {e}"
        ) from e

    # Load workbook to check available sheets
    wb = load_workbook(filename=source_file, data_only=True)

    data_dir = Path(__file__).resolve().parents[0] / "data"
    prepared_dir = data_dir / "prepared"
    prepared_dir.mkdir(exist_ok=True)

    # Process configured sheets
    processed_sheets = set()
    for sheet_name, sheet_config in sheet_configs.items():
        # Skip sheets that don't exist in the workbook
        if sheet_name not in wb.sheetnames:
            print(f"Warning: Sheet '{sheet_name}' not found in workbook, skipping")
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
        df.to_parquet(output_path)
        print(f"Saved {output_path}")

        # Save as CSV
        csv_output_path = prepared_dir / f"{sanitized_name}.csv"
        df.to_csv(csv_output_path, index=False)
        print(f"Saved {csv_output_path}")

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
        "Sheet2"
    ]

    print(f"\nProcessing {len(supporting_tables)} additional supporting tables...")

    for sheet_name in supporting_tables:
        if sheet_name in wb.sheetnames and sheet_name not in processed_sheets:
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
                    c for c in sheet_name if c.isalnum() or c in (" ", "_", "-", "(", ")")
                ).rstrip()
                sanitized_name = sanitized_name.lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")

                # Save as Parquet
                output_path = prepared_dir / f"{sanitized_name}.parquet"
                df.to_parquet(output_path)
                print(f"Saved supporting table: {output_path}")

                # Save as CSV
                csv_output_path = prepared_dir / f"{sanitized_name}.csv"
                df.to_csv(csv_output_path, index=False)
                print(f"Saved supporting table: {csv_output_path}")

            except Exception as e:
                print(f"Warning: Could not process supporting table '{sheet_name}': {e}")

    wb.close()
    print(f"\nData preparation complete. Processed {len(processed_sheets)} configured sheets and additional supporting tables.")


if __name__ == "__main__":
    main()
