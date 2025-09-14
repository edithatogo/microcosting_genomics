from genomics_microcosting.calculation_engine import CalculationEngine

engine = CalculationEngine()
print(f"Loaded sheets: {engine.get_sheet_names()}")
