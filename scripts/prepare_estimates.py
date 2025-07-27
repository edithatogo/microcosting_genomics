from pathlib import Path
import pandas as pd
from unimelb_phd_phase_1.config import load_config
from prepare_data import _parse_generic_sheet


def main() -> None:
    config = load_config()
    workbook_key = config.get("default_workbook", "main")
    source_file = Path(config["workbooks"][workbook_key]["path"])
    sheet = config["workbooks"][workbook_key]["sheets"]["estimates"]

    out_dir = Path(__file__).resolve().parents[0] / "data" / "prepared"
    out_dir.mkdir(exist_ok=True)

    df = _parse_generic_sheet(source_file, sheet, header_rows=3, skip_rows=1)
    df.to_parquet(out_dir / "3._estimates.parquet")
    print("Saved 3._estimates.parquet")


if __name__ == "__main__":
    main()
