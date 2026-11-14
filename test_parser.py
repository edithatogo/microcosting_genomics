# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Exercise the formula parser from the command line."""

import sys

from genomics_microcosting.formula_parser import parse_formula

# Test parsing a cross-sheet reference
formula = "='Labour - Usage - VCGS'!C5"
parsed = parse_formula(formula)
sys.stdout.writelines((f"Formula: {formula}", "\n"))
sys.stdout.writelines((f"Parsed: {parsed}", "\n"))

# Test another formula
formula2 = "='BI - Comp Stor Costs - VCGS'!V$3"
parsed2 = parse_formula(formula2)
sys.stdout.writelines((f"\nFormula: {formula2}", "\n"))
sys.stdout.writelines((f"Parsed: {parsed2}", "\n"))
