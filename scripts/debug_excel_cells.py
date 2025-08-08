import openpyxl

excel_file_path = (
    "data/Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm"
)
workbook = openpyxl.load_workbook(excel_file_path, data_only=False)
sheet = workbook["Detailed Table"]


def inspect_cell(cell_ref):
    cell = sheet[cell_ref]
    print(f"--- Cell {cell_ref} ---")
    print(f"Value: {cell.value}")
    print(f"Data Type: {cell.data_type}")

    is_merged = False
    merged_range_info = None
    for merged_range in sheet.merged_cells.ranges:
        if cell_ref in merged_range:
            is_merged = True
            merged_range_info = merged_range
            break

    print(f"Is Merged: {is_merged}")
    if is_merged:
        print(f"  Part of merged range: {merged_range_info}")
        top_left_cell_value = sheet.cell(
            row=merged_range_info.min_row, column=merged_range_info.min_col
        ).value
        print(f"  Top-left cell of merged range value: {top_left_cell_value}")


inspect_cell("A4")
inspect_cell("M4")
