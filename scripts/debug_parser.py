# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Inspect parsing of a representative cross-sheet reference."""

import sys

from genomics_microcosting.formula_parser import parse_formula

if __name__ == "__main__":
    formula = "='Labour - Usage - VCGS'!AA5"
    sys.stdout.write(f"{parse_formula(formula)}\n")
