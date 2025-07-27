from pathlib import Path
import pandas as pd

from unimelb_phd_phase_1.excel_utils import load_sheet_with_headers


def test_load_sheet_with_headers():
    file = Path(__file__).resolve().parent / "test_data.xlsx"
    df = load_sheet_with_headers(file, "Sheet1", header_rows=2)

    assert isinstance(df.columns, pd.MultiIndex)
    assert df.columns[0][0] == "col1"
    assert df.dtypes.iloc[0] == "int64"
    assert df.dtypes.iloc[2] == "float64"
