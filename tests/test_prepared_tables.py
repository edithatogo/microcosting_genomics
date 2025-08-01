from pathlib import Path

import pandas as pd

PREP_DIR = Path("data/prepared")


def test_labor_prices_table():
    df = pd.read_parquet(PREP_DIR / "2._labor_prices.parquet")
    assert df.shape[0] == 79
    assert {"Jurisdiction", "Personnel type", "Label"}.issubset(df.columns)


def test_estimates_table():
    df = pd.read_parquet(PREP_DIR / "3._estimates.parquet")
    assert df.shape[0] == 77
    assert df.shape[1] == 16

