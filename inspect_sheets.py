import openpyxl


def inspect_sheets(file_path):
    """Prints the first 5 rows of each sheet in an Excel file."""
    workbook = openpyxl.load_workbook(file_path, read_only=True)
    for sheet_name in workbook.sheetnames:
        print(f"--- Sheet: {sheet_name} ---")
        sheet = workbook[sheet_name]
        for row in sheet.iter_rows(min_row=1, max_row=5):
            print([cell.value for cell in row])
        print("\n")


if __name__ == "__main__":
    inspect_sheets(
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
