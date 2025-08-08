import openpyxl


def list_sheet_names(file_path):
    """Lists the sheet names in an Excel file."""
    workbook = openpyxl.load_workbook(file_path, read_only=True)
    print("Sheet names:")
    for sheet_name in workbook.sheetnames:
        print(f"- {sheet_name}")


if __name__ == "__main__":
    list_sheet_names(
        "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
    )
