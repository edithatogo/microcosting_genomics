from genomics_microcosting.formula_parser import parse_formula

# Test parsing a cross-sheet reference
formula = "='Labour - Usage - VCGS'!C5"
parsed = parse_formula(formula)
print(f"Formula: {formula}")
print(f"Parsed: {parsed}")

# Test another formula
formula2 = "='BI - Comp Stor Costs - VCGS'!V$3"
parsed2 = parse_formula(formula2)
print(f"\nFormula: {formula2}")
print(f"Parsed: {parsed2}")
