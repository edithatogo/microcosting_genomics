# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Inspect parsed cross-sheet formulas from the command line."""

import re
import sys

from genomics_microcosting.formula_parser import parse_formula

# Test the problematic formula
formula = "'BI - Comp+Stor Costs - VCGS'!V$3"
sys.stdout.writelines((" ".join(("Testing formula:", str(repr(formula)))), "\n"))

# Test the cross-sheet reference pattern
pattern = r"'([^']*)'!(\$?[A-Za-z]+\$?\d+)"
match = re.fullmatch(pattern, formula)
if match:
    sheet, cell = match.groups()
    sys.stdout.writelines(
        (str("Match found: sheet=" + repr(sheet) + ", cell=" + repr(cell)), "\n"),
    )
else:
    sys.stdout.writelines(("No match found", "\n"))

# Test parsing
result = parse_formula("=" + formula)
sys.stdout.writelines((" ".join(("Parse result:", str(result))), "\n"))
