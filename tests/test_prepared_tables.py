from pathlib import Path
import pandas as pd

PREPARED = Path(__file__).resolve().parents[1] / "data" / "prepared"


def test_labor_prices_shape():
    df = pd.read_parquet(PREPARED / "2._labor_prices.parquet")
    assert list(df.columns[:3]) == ["Jurisdiction", "Personnel type", "Label"]
    assert len(df) == 30


def test_estimates_shape():
    df = pd.read_parquet(PREPARED / "3._estimates.parquet")
    assert len(df) == 74
    assert df.columns[0].startswith("Unnamed")
