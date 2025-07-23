from unimelb_phd_phase_1.calculation_engine import CalculationEngine

engine = CalculationEngine()
print(f"Loaded sheets: {engine.get_sheet_names()}")