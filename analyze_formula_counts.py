import csv
from pathlib import Path

def analyze_formulas(file_path: Path):
    total_formulas = 0
    unique_formulas = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                for cell in row:
                    if cell and cell.startswith('='):
                        total_formulas += 1
                        unique_formulas.add(cell)
    except FileNotFoundError:
        return 0, 0
    return total_formulas, len(unique_formulas)

if __name__ == "__main__":
    files_to_analyze = [
        "data/extracted/BI___CompStor_Costs___VCGS_formulas.csv",
        "data/extracted/Labour___Costs___VCGS_formulas.csv",
        "data/extracted/Cons____Costs_and_Util___VCGS_formulas.csv",
    ]
    print("Sheet Name,Total Formulas,Unique Formulas")
    for file_str in files_to_analyze:
        file_path = Path(file_str)
        # Sanitize the name for better readability
        sheet_name = file_path.stem.replace('_formulas', '').replace('___', ' - ').replace('____', ' - ').replace('_', ' ')
        total, unique = analyze_formulas(file_path)
        print(f'"{sheet_name}",{total},{unique}')
