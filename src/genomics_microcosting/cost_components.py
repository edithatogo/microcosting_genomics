"""Abstract Cost Components for Genomics Microcosting.

This module defines abstract base classes for different types of cost components
in the microcosting system. These abstractions provide a higher-level interface
for cost calculations while maintaining the flexibility of the strategy pattern.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from numbers import Number


class CostComponent(ABC):
    """Abstract base class for all cost components.

    This class defines the common interface that all cost components must implement.
    Cost components represent different types of calculations used in microcosting.
    """

    def __init__(self, name: str):
        """Initialize the cost component.

        Args:
            name: A descriptive name for this cost component
        """
        self.name = name

    @abstractmethod
    def calculate(self, engine, parsed_formula: Dict[str, Any], sheet_name: str, cell_ref: str) -> Optional[Number]:
        """Calculate the cost using this component.

        Args:
            engine: The calculation engine instance
            parsed_formula: The parsed formula data
            sheet_name: Name of the sheet containing the formula
            cell_ref: Cell reference of the formula

        Returns:
            The calculated cost value, or None if calculation fails
        """
        pass

    @abstractmethod
    def get_component_type(self) -> str:
        """Get the type of this cost component.

        Returns:
            String identifier for the component type
        """
        pass

    @abstractmethod
    def validate_inputs(self, parsed_formula: Dict[str, Any]) -> bool:
        """Validate that the parsed formula has required inputs for this component.

        Args:
            parsed_formula: The parsed formula to validate

        Returns:
            True if inputs are valid, False otherwise
        """
        pass


class ArithmeticCostComponent(CostComponent):
    """Abstract base class for arithmetic cost components.

    This class handles basic mathematical operations like addition, multiplication,
    division, and other arithmetic calculations.
    """

    @abstractmethod
    def get_operation_type(self) -> str:
        """Get the specific arithmetic operation type.

        Returns:
            String identifier for the arithmetic operation (e.g., 'addition', 'multiplication')
        """
        pass

    @abstractmethod
    def get_operand_count(self) -> int:
        """Get the number of operands this operation requires.

        Returns:
            Number of operands (0 for variable count)
        """
        pass


class ReferenceCostComponent(CostComponent):
    """Abstract base class for reference-based cost components.

    This class handles operations that reference other cells or ranges,
    such as direct cell references and lookup operations.
    """

    @abstractmethod
    def get_reference_type(self) -> str:
        """Get the type of reference this component handles.

        Returns:
            String identifier for the reference type (e.g., 'cell', 'range', 'lookup')
        """
        pass

    @abstractmethod
    def resolve_reference(self, engine, reference: Dict[str, Any], sheet_name: str) -> Any:
        """Resolve a reference to its actual value.

        Args:
            engine: The calculation engine instance
            reference: The reference data to resolve
            sheet_name: Name of the current sheet

        Returns:
            The resolved value
        """
        pass


class AggregateCostComponent(CostComponent):
    """Abstract base class for aggregate cost components.

    This class handles operations that aggregate multiple values,
    such as sum, average, count, etc.
    """

    @abstractmethod
    def get_aggregation_type(self) -> str:
        """Get the type of aggregation this component performs.

        Returns:
            String identifier for the aggregation type (e.g., 'sum', 'average', 'count')
        """
        pass

    @abstractmethod
    def get_range_specification(self) -> Dict[str, Any]:
        """Get the range specification for this aggregation.

        Returns:
            Dictionary describing the range (e.g., {'type': 'cells', 'count': 2})
        """
        pass


class FinancialCostComponent(CostComponent):
    """Abstract base class for financial cost components.

    This class handles financial calculations like loan payments, depreciation,
    present value calculations, etc.
    """

    @abstractmethod
    def get_financial_function(self) -> str:
        """Get the financial function this component implements.

        Returns:
            String identifier for the financial function (e.g., 'pmt', 'pv', 'fv')
        """
        pass

    @abstractmethod
    def get_required_parameters(self) -> list[str]:
        """Get the list of required parameters for this financial function.

        Returns:
            List of parameter names required for the calculation
        """
        pass


class ConditionalCostComponent(CostComponent):
    """Abstract base class for conditional cost components.

    This class handles conditional operations like if-then-else logic,
    error handling, and other conditional calculations.
    """

    @abstractmethod
    def get_condition_type(self) -> str:
        """Get the type of condition this component handles.

        Returns:
            String identifier for the condition type (e.g., 'if', 'iferror', 'switch')
        """
        pass

    @abstractmethod
    def evaluate_condition(self, condition: Any) -> bool:
        """Evaluate a condition to determine the execution path.

        Args:
            condition: The condition to evaluate

        Returns:
            True if condition is met, False otherwise
        """
        pass


class ComplexCostComponent(CostComponent):
    """Abstract base class for complex cost components.

    This class handles complex expressions that combine multiple operations,
    nested calculations, and advanced formula patterns.
    """

    @abstractmethod
    def get_complexity_level(self) -> str:
        """Get the complexity level of this component.

        Returns:
            String identifier for complexity level (e.g., 'simple', 'intermediate', 'advanced')
        """
        pass

    @abstractmethod
    def decompose_expression(self, parsed_formula: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Decompose a complex expression into simpler components.

        Args:
            parsed_formula: The complex formula to decompose

        Returns:
            List of decomposed simpler expressions
        """
        pass