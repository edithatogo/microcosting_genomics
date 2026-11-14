# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Translate worksheet coordinates and Excel cell references."""

import re


def coords_to_cell(row: int, col: int) -> str:
    """Convert (row, col) tuple to cell string.

    Converts zero-based row and column indices to Excel-style cell references.
    For example, (0, 0) becomes "A1", (1, 2) becomes "C2".

    Args:
        row (int): Zero-based row index.
        col (int): Zero-based column index.

    Returns:
        str: Excel-style cell reference (e.g., "A1").

    """
    col_str = ""
    while col >= 0:
        col_str = chr(ord("A") + col % 26) + col_str
        col = col // 26 - 1
    return f"{col_str}{row + 1}"


def cell_to_coords(cell_str: object) -> tuple[int, int] | tuple[None, None]:
    """Convert cell string to (row, col) tuple.

    Converts Excel-style cell references to zero-based row and column indices.
    For example, "A1" becomes (0, 0), "C2" becomes (1, 2).
    Handles cell references with $ signs (e.g., "$A$1").

    Args:
        cell_str (str): Excel-style cell reference (e.g., "A1" or "$A$1").

    Returns:
        tuple: A tuple of (row, col) as zero-based indices, or (None, None) if invalid.

    """
    if not isinstance(cell_str, str):
        return None, None
    # Remove $ signs
    cell_str = cell_str.replace("$", "")
    match = re.match(r"([A-Z]+)([0-9]+)", cell_str)
    if match is None:
        return None, None
    try:
        col_str, row_str = match.groups()
        col = 0
        for char in col_str:
            col = col * 26 + (ord(char) - ord("A") + 1)
        return int(row_str) - 1, col - 1
    except AttributeError:
        return None, None
