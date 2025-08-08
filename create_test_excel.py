import pandas as pd

# Create a new Excel file with some test data
df1 = pd.DataFrame(
    {"col1": [1, 2, 3], "col2": [4, 5, 6], "col3": ["=A2*B2", "=A3*B3", "=A4*B4"]}
)

df2 = pd.DataFrame({"colA": [10, 20, 30], "colB": [40, 50, 60]})

with pd.ExcelWriter("tests/test_data.xlsx") as writer:
    df1.to_excel(writer, sheet_name="Sheet1", index=False)
    df2.to_excel(writer, sheet_name="Sheet2", index=False)
