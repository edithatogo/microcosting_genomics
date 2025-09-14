from genomics_microcosting.formula_parser import parse_formula

formula = "='Labour - Usage - VCGS'!AA5"
parsed = parse_formula(formula)
print(parsed)
