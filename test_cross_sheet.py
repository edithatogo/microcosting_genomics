#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0

"""Exercise cross-sheet formulas from the command line."""

import sys

from src.genomics_microcosting.formula_parser import parse_formula

# Test cross-sheet reference parsing
formula = "='BI - Comp Stor Costs - VCGS'!V$3"
sys.stdout.writelines((f"Testing formula: {formula!r}", "\n"))
result = parse_formula(formula)
sys.stdout.writelines((f"Parsed result: {result}", "\n"))

# Test another cross-sheet reference
formula2 = "='BI - Comp Stor Costs - VCGS'!I$15"
sys.stdout.writelines((f"\nTesting formula: {formula2!r}", "\n"))
result2 = parse_formula(formula2)
sys.stdout.writelines((f"Parsed result: {result2}", "\n"))
