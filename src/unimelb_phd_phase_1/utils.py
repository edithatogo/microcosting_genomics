import re


def coords_to_cell(row, col):
    """Convert (row, col) tuple to cell string."""
    col_str = ""
    while col >= 0:
        col_str = chr(ord("A") + col % 26) + col_str
        col = col // 26 - 1
    return f"{col_str}{row + 1}"


def cell_to_coords(cell_str):
    """Convert cell string to (row, col) tuple."""
    if not isinstance(cell_str, str):
        return None, None
    # Remove $ signs
    cell_str = cell_str.replace("$", "")
    try:
        col_str, row_str = re.match(r"([A-Z]+)([0-9]+)", cell_str).groups()
        col = 0
        for char in col_str:
            col = col * 26 + (ord(char) - ord("A") + 1)
        return int(row_str) - 1, col - 1
    except AttributeError:
        return None, None
