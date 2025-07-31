import pandas as pd
from pathlib import Path

PREP_DIR = Path("data/prepared")

def get_row_counts():
    labor_prices_df = pd.read_parquet(PREP_DIR / "2._labor_prices.parquet")
    estimates_df = pd.read_parquet(PREP_DIR / "3._estimates.parquet")
    print(f"Labor prices row count: {labor_prices_df.shape[0]}")
    print(f"Estimates row count: {estimates_df.shape[0]}")

if __name__ == "__main__":
    get_row_counts()
