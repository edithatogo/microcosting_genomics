import pandas as pd
from pathlib import Path

PREP_DIR = Path("data/prepared")

def get_row_counts():
    for f in sorted(PREP_DIR.glob("*.parquet")):
        df = pd.read_parquet(f)
        print(f"{f.name} row count: {df.shape[0]}")

if __name__ == "__main__":
    get_row_counts()
