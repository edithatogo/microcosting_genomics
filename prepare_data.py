# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Legacy workbook preparation command."""

from genomics_microcosting.prepare_data import (
    create_unique_column_names,
    main,
    parse_reference_sheet,
)

__all__ = ["create_unique_column_names", "main"]
_parse_generic_sheet = parse_reference_sheet

if __name__ == "__main__":
    main()
