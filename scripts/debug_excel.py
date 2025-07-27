import openpyxl

def debug_excel():
    """
    A script to debug the test_data.xlsx file.
    """
    print("Starting Excel debug script...")

    # Load the workbook
    workbook = openpyxl.load_workbook('tests/test_data.xlsx')

    # Get the sheet
    sheet = workbook['Sheet1']

    # Get the value of cell A2
    value = sheet['A2'].value

    # Print the value
    print(f"Value of A2: {value}")

if __name__ == "__main__":
    debug_excel()
