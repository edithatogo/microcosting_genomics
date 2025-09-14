#!/usr/bin/env python3

from src.genomics_microcosting.formula_parser import parse_formula

# Test cross-sheet reference parsing
formula = "='BI - Comp Stor Costs - VCGS'!V$3"
print(f"Testing formula: {repr(formula)}")
result = parse_formula(formula)
print(f"Parsed result: {result}")

# Test another cross-sheet reference
formula2 = "='BI - Comp Stor Costs - VCGS'!I$15"
print(f"\nTesting formula: {repr(formula2)}")
result2 = parse_formula(formula2)
print(f"Parsed result: {result2}")