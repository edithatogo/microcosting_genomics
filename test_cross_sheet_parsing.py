import re
from genomics_microcosting.formula_parser import parse_formula

# Test the problematic formula
formula = "'BI - Comp+Stor Costs - VCGS'!V$3"
print('Testing formula:', repr(formula))

# Test the cross-sheet reference pattern
pattern = r"'([^']*)'!(\$?[A-Za-z]+\$?\d+)"
match = re.fullmatch(pattern, formula)
if match:
    sheet, cell = match.groups()
    print('Match found: sheet=' + repr(sheet) + ', cell=' + repr(cell))
else:
    print('No match found')

# Test parsing
result = parse_formula('=' + formula)
print('Parse result:', result)
