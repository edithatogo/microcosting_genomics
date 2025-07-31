from pathlib import Path

import pandas as pd

from unimelb_phd_phase_1.excel_utils import load_sheet_with_headers


def test_load_sheet_with_headers():
    file = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
    df = load_sheet_with_headers(
        file,
        "1. Detailed Table",
        header_rows=5,
        string_columns=["Test", "Category", "Sub-Category", "Step"],
    )
    assert isinstance(df.columns, pd.MultiIndex)
    assert df.columns[0][1] == "Test"
    assert df.dtypes.iloc[0] == object
    assert df.dtypes.iloc[4] == "float64"
