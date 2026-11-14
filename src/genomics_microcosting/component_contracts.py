# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Structural contracts for optional formula-strategy metadata capabilities."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ComponentMetadata(Protocol):
    """Advertise the existing get_component_type capability."""

    def get_component_type(self) -> str:
        """Return the declared metadata or validation result."""
        ...


@runtime_checkable
class InputValidation(Protocol):
    """Advertise the existing validate_inputs capability."""

    def validate_inputs(self, parsed_formula: dict[str, object]) -> bool:
        """Return the declared metadata or validation result."""
        ...


@runtime_checkable
class OperationMetadata(Protocol):
    """Advertise the existing get_operation_type capability."""

    def get_operation_type(self) -> str:
        """Return the declared metadata or validation result."""
        ...


@runtime_checkable
class ReferenceMetadata(Protocol):
    """Advertise the existing get_reference_type capability."""

    def get_reference_type(self) -> str:
        """Return the declared metadata or validation result."""
        ...


@runtime_checkable
class AggregationMetadata(Protocol):
    """Advertise the existing get_aggregation_type capability."""

    def get_aggregation_type(self) -> str:
        """Return the declared metadata or validation result."""
        ...


@runtime_checkable
class FinancialMetadata(Protocol):
    """Advertise the existing get_financial_function capability."""

    def get_financial_function(self) -> str:
        """Return the declared metadata or validation result."""
        ...


@runtime_checkable
class RequiredParameters(Protocol):
    """Advertise the existing get_required_parameters capability."""

    def get_required_parameters(self) -> list[str]:
        """Return the declared metadata or validation result."""
        ...


@runtime_checkable
class ConditionMetadata(Protocol):
    """Advertise the existing get_condition_type capability."""

    def get_condition_type(self) -> str:
        """Return the declared metadata or validation result."""
        ...


@runtime_checkable
class ComplexityMetadata(Protocol):
    """Advertise the existing get_complexity_level capability."""

    def get_complexity_level(self) -> str:
        """Return the declared metadata or validation result."""
        ...
