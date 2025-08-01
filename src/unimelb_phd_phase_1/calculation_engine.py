import logging
from pathlib import Path

from .formula_parser import parse_formula
from .strategies import (
    AdditionStrategy,
    DivisionStrategy,
    IfErrorStrategy,
    IfStrategy,
    LiteralStrategy,
    MultiplicationStrategy,
    PmtStrategy,
    ReferenceStrategy,
    StringLiteralStrategy,
    SumCellsStrategy,
    SumRangeStrategy,
    UnknownStrategy,
    VLookupStrategy,
)
from .sheet_manager import SheetManager
from .utils import cell_to_coords, coords_to_cell

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CalculationEngine:
    def __init__(
        self,
        sheet_manager: SheetManager,
        verbose: bool = False,
    ):
        """Create a new engine instance."""
        self.logger = logger.getChild(self.__class__.__name__)
        level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(levelname)s:%(name)s:%(message)s")
            )
            self.logger.addHandler(handler)

        self.sheet_manager = sheet_manager
        self.memoization_cache = {}
        self.call_stack = []
        self.strategy_map = {
            "literal": LiteralStrategy(),
            "string_literal": StringLiteralStrategy(),
            "reference": ReferenceStrategy(),
            "multiplication": MultiplicationStrategy(),
            "addition": AdditionStrategy(),
            "division": DivisionStrategy(),
            "sum_range": SumRangeStrategy(),
            "sum_cells": SumCellsStrategy(),
            "if": IfStrategy(),
            "iferror": IfErrorStrategy(),
            "vlookup": VLookupStrategy(),
            "pmt": PmtStrategy(),
            "unknown": UnknownStrategy(),
        }

    def get_cell_value(self, sheet_name, cell_ref):
        row_idx, col_idx = cell_to_coords(cell_ref)
        if row_idx is None or col_idx is None:
            return None
        
        df = self.sheet_manager.get_data(sheet_name)
        if df is None:
            return None

        config = self.sheet_manager.sheet_configs.get(sheet_name)
        if not config:
            return None

        data_starts_at = config.get("data_starts_at", 2)
        df_row_idx = row_idx - (data_starts_at - 1)

        if 0 <= df_row_idx < len(df):
            return df.iloc[df_row_idx, col_idx]
        return None

    def get_cell_formula(self, sheet_name, cell_ref):
        row_idx, col_idx = cell_to_coords(cell_ref)
        if row_idx is None or col_idx is None:
            return None
        
        df = self.sheet_manager.get_formulas(sheet_name)
        if df is None:
            return None
            
        config = self.sheet_manager.sheet_configs.get(sheet_name)
        if not config:
            return None

        data_starts_at = config.get("data_starts_at", 2)
        df_row_idx = row_idx - (data_starts_at - 1)

        if 0 <= df_row_idx < len(df):
            formula = df.iloc[df_row_idx, col_idx]
            if isinstance(formula, str) and formula.startswith("="):
                return formula
            return None
        return None

    def execute_formula(self, formula_or_parsed, sheet_name, cell_ref):
        if (sheet_name, cell_ref) in self.call_stack:
            raise Exception(
                f"Circular reference detected: {self.call_stack + [(sheet_name, cell_ref)]}"
            )
        self.call_stack.append((sheet_name, cell_ref))

        if (sheet_name, cell_ref) in self.memoization_cache:
            self.call_stack.pop()
            return self.memoization_cache[(sheet_name, cell_ref)]

        if isinstance(formula_or_parsed, dict):
            parsed_formula = formula_or_parsed
        elif isinstance(formula_or_parsed, str):
            parsed_formula = parse_formula(formula_or_parsed)
        else:
            self.call_stack.pop()
            return formula_or_parsed

        if parsed_formula is None:
            self.call_stack.pop()
            return None

        strategy = self.strategy_map.get(parsed_formula["type"])

        if strategy:
            result = strategy.execute(self, parsed_formula, sheet_name, cell_ref)
        else:
            result = f"UNSUPPORTED[{parsed_formula['type']}]"

        self.memoization_cache[(sheet_name, cell_ref)] = result
        self.call_stack.pop()
        return result

    def run_engine(self, sheet_name: str | None = None, fail_on_error: bool = True):
        """
        Runs the calculation engine on the specified sheet and returns a DataFrame with the results.
        If fail_on_error is False, it will log errors and continue.
        """
        if sheet_name is None:
            sheet_name = self.sheet_manager.default_sheet_names["detailed_table"]
        formulas_df = self.sheet_manager.get_formulas(sheet_name)
        if formulas_df is None:
            return None, []

        results_df = formulas_df.copy()
        errors = []
        for r_idx in range(formulas_df.shape[0]):
            for c_idx in range(formulas_df.shape[1]):
                formula = formulas_df.iloc[r_idx, c_idx]
                cell_ref = coords_to_cell(
                    r_idx
                    + self.sheet_manager.sheet_configs.get(sheet_name, {"data_starts_at": 1})[
                        "data_starts_at"
                    ]
                    - 1,
                    c_idx,
                )
                if isinstance(formula, str) and formula.startswith("="):
                    try:
                        result = self.execute_formula(formula, sheet_name, cell_ref)
                        results_df.iloc[r_idx, c_idx] = result
                    except Exception as e:
                        error_info = {
                            "cell": cell_ref,
                            "formula": formula,
                            "error": str(e),
                            "call_stack": self.call_stack,
                        }
                        errors.append(error_info)
                        results_df.iloc[r_idx, c_idx] = f"ERROR[{str(e)}]"
                        if fail_on_error:
                            raise
                else:
                    value = self.get_cell_value(sheet_name, cell_ref)
                    results_df.iloc[r_idx, c_idx] = value
        return results_df, errors