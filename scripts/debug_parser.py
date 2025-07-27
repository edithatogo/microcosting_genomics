from unimelb_phd_phase_1.formula_parser import parse_formula

formula = "='Labour - Usage - VCGS'!AA5"
parsed = parse_formula(formula)
print(parsed)
