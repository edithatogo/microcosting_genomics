from pathlib import Path
import pandas as pd
from unimelb_phd_phase_1.config import load_config
from prepare_data import _parse_generic_sheet


def main() -> None:
    config = load_config()
    workbook_key = config.get("default_workbook", "main")
    source_file = Path(config["workbooks"][workbook_key]["path"])
    sheet = config["workbooks"][workbook_key]["sheets"]["labor_prices"]

    out_dir = Path(__file__).resolve().parents[0] / "data" / "prepared"
    out_dir.mkdir(exist_ok=True)

    df = _parse_generic_sheet(source_file, sheet, header_rows=2)
    df.to_parquet(out_dir / "2._labor_prices.parquet")
    print("Saved 2._labor_prices.parquet")


if __name__ == "__main__":
    main()
