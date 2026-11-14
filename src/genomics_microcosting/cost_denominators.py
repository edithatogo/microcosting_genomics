# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Describe declared-result ratios without inferring issued reports or prices."""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Literal

from genomics_microcosting.workload_contract import Workload

CostServiceScope = Literal[
    "static_projection",
    "complete_modeled_workload",
    "partial_modeled_workload",
]
MAX_DECIMAL_DIGITS = 128


@dataclass(frozen=True)
class ReportableCostSummary:
    """Keep count knowledge, service coverage and the declared-result ratio apart."""

    format_version: Literal["reportable-cost-v1"]
    declared_result_count: int | None
    count_state: Literal["unknown", "zero", "positive"]
    service_scope: CostServiceScope
    selected_cost_known: bool
    unit_cost_per_declared_reportable_result: Fraction | None


def _cost_fraction(value: Decimal | Fraction | int) -> Fraction:
    if isinstance(value, Decimal) and not value.is_zero():
        parts = value.as_tuple()
        if (
            not isinstance(parts.exponent, int)
            or abs(parts.exponent) > MAX_DECIMAL_DIGITS
            or len(parts.digits) > MAX_DECIMAL_DIGITS
        ):
            msg = "Reportable cost exceeds Decimal conversion profile bounds"
            raise ValueError(msg)
    if isinstance(value, Decimal) and value.is_zero():
        return Fraction()
    return Fraction(value)


def summarize_reportable_cost(
    workload: Workload,
    selected_cost: Decimal | Fraction | int | None,
    *,
    service_scope: CostServiceScope,
) -> ReportableCostSummary:
    """Derive a ratio for unique declared results; do not validate source costs.

    Args:
        workload: Declared cohort and nullable result relationships.
        selected_cost: Exact selected model cost, or an explicitly unknown cost.
        service_scope: Static projection or recomputed modeled-service coverage.

    Returns:
        Distinct unknown/zero/positive counts and an optional exact ratio.

    Raises:
        TypeError: Cost is not an exact supported scalar or explicit unknown.
        ValueError: Workload, scope, finite amount or conversion bounds fail.

    """
    workload = Workload.model_validate(workload)
    if service_scope not in (
        "static_projection",
        "complete_modeled_workload",
        "partial_modeled_workload",
    ):
        msg = "Reportable cost service scope is unsupported"
        raise ValueError(msg)
    if selected_cost is not None:
        if (
            not isinstance(selected_cost, (Decimal, Fraction))
            and type(
                selected_cost,
            )
            is not int
        ):
            msg = "Reportable cost requires an exact numeric scalar or None"
            raise TypeError(msg)
        if (
            isinstance(selected_cost, Decimal) and not selected_cost.is_finite()
        ) or selected_cost < 0:
            msg = "Reportable cost must be finite and nonnegative"
            raise ValueError(msg)
    count = workload.entity_counts()["reportable_results"]
    state: Literal["unknown", "zero", "positive"] = (
        "unknown" if count is None else "zero" if count == 0 else "positive"
    )
    ratio = (
        _cost_fraction(selected_cost) / count
        if count
        and selected_cost is not None
        and service_scope != "partial_modeled_workload"
        else None
    )
    return ReportableCostSummary(
        "reportable-cost-v1",
        count,
        state,
        service_scope,
        selected_cost is not None,
        ratio,
    )
