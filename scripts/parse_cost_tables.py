"""Parse cost-related tables and save them as Parquet files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from prepare_data import create_unique_column_names


def _parse_generic_csv(path: Path | str, header_rows: int) -> pd.DataFrame:
    """Parse a CSV file that contains multiple header rows."""
    df_raw = pd.read_csv(path, header=None)
    header_df = df_raw.iloc[:header_rows].ffill(axis=0)

    columns: list[str] = []
    for i in range(header_df.shape[1]):
        parts = [str(v).strip() for v in header_df.iloc[:, i].values if pd.notna(v)]
        name = " ".join(parts).replace("nan", "").strip()
        name = " ".join(name.split())
        if not name:
            name = f"unnamed_{i}"
        columns.append(name)

    data_df = df_raw.iloc[header_rows:].reset_index(drop=True)
    data_df.columns = create_unique_column_names(columns)

    for col in data_df.columns:
        data_df[col] = pd.to_numeric(data_df[col], errors="coerce")

    return data_df


def parse_equipment_costs(path: Path) -> pd.DataFrame:
    """Parse the equipment costs table."""
    return _parse_generic_csv(path, header_rows=4)


def parse_consumable_costs(path: Path) -> pd.DataFrame:
    """Parse the consumable costs table."""
    return _parse_generic_csv(path, header_rows=3)


def parse_labour_costs(path: Path) -> pd.DataFrame:
    """Parse the labour costs table."""
    return _parse_generic_csv(path, header_rows=2)


def main() -> None:
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
        df.to_parquet(prepared_dir / name)
        print(f"Saved {name}")


if __name__ == "__main__":
    main()
