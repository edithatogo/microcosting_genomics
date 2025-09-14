from genomics_microcosting.calculation_engine import CalculationEngine


def setup_engine():
    """
    Initializes and sets up the calculation engine.
    """
    print("Setting up the calculation engine...")
    engine = CalculationEngine()
    print("Calculation engine setup complete.")
    print(f"Loaded sheets: {engine.get_sheet_names()}")
    return engine


if __name__ == "__main__":
    engine = setup_engine()
    # The 'engine' object is now ready for use.
    # You can now interact with it, for example, by getting data from a sheet:
    # detailed_table_data = engine.get_data('Detailed Table')
    # print(detailed_table_data.head())
