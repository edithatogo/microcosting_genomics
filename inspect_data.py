import pandas as pd


def inspect_data():
    """
    Inspects a specific cell in the detailed_table_formulas.parquet file.
    """
    df = pd.read_parquet("data/prepared/detailed_table_formulas.parquet")
    value = df.at[428, "Test"]
    print(f"The value at row 428, column 'Test' is: '{value}'")
    print(f"The type of the value is: {type(value)}")


if __name__ == "__main__":
    inspect_data()
