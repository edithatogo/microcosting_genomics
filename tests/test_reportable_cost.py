# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Declared result denominators remain distinct from demand and service coverage."""

import json
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from typing import cast
lazy from pathlib import Path

import pytest

from genomics_microcosting.cost_denominators import summarize_reportable_cost
from genomics_microcosting.dynamic_batch import AvailabilityWindow
from genomics_microcosting.static_batch_cost import (
    calculate_dynamic_batch_cost,
    calculate_static_batch_cost,
)
from genomics_microcosting.workflow_cost import calculate_workflow_cost
from tests.checks import require_equal
from tests.test_dynamic_batch import dynamic, timed
from tests.test_inventory_ledger import restock
from tests.test_static_batch import policy
from tests.test_static_batch_cost import batch_inputs
from tests.test_workflow_cost import cost_inputs
lazy from genomics_microcosting.workload_contract import Workload


def results(
    workload: Workload,
    ids: tuple[tuple[str, ...] | None, ...],
) -> Workload:
    """Declare result relationships without inventing observed report events."""
    return workload.model_copy(
        update={
            "cases": tuple(
                case.model_copy(update={"reportable_result_ids": value})
                for case, value in zip(workload.cases, ids, strict=True)
            ),
        },
    )


@pytest.mark.parametrize(
    ("cost", "error"),
    [
        (Decimal("NaN"), ValueError),
        (Decimal("Infinity"), ValueError),
        (Decimal(-1), ValueError),
        (-1, ValueError),
        (0.1, TypeError),
        (True, TypeError),
    ],
)
def test_invalid_costs_cannot_be_hidden_by_an_unknown_denominator(
    cost: object,
    error: type[Exception],
) -> None:
    """Even an undefined ratio does not accept nonfinite or inexact cost input."""
    with pytest.raises(error):
        summarize_reportable_cost(
            timed(1),
            cast("Decimal | Fraction | int | None", cost),
            service_scope="complete_modeled_workload",
        )


@pytest.mark.parametrize(
    ("cost", "ratio"),
    [
        (None, None),
        (Decimal(0), Fraction(0)),
        (1, Fraction(1)),
        (Fraction(1, 3), Fraction(1, 3)),
    ],
)
def test_unknown_and_exact_zero_or_rational_numerators_remain_distinct(
    cost: Decimal | Fraction | int | None,
    ratio: Fraction | None,
) -> None:
    """Unknown cost is not zero; already exact fractions stay exact."""
    value = summarize_reportable_cost(
        results(timed(1), (("r1",),)),
        cost,
        service_scope="complete_modeled_workload",
    )
    require_equal(value.declared_result_count, 1)
    require_equal(value.selected_cost_known, expected=cost is not None)
    require_equal(value.unit_cost_per_declared_reportable_result, ratio)


@pytest.mark.parametrize("amount", ["1e1000", "9." + "1" * 129])
def test_decimal_conversion_bounds_precede_exact_ratio_construction(
    amount: str,
) -> None:
    """Compact extreme Decimal representations cannot expand without bounds."""
    with pytest.raises(ValueError, match="conversion profile bounds"):
        summarize_reportable_cost(
            results(timed(1), (("r1",),)),
            Decimal(amount),
            service_scope="static_projection",
        )


@pytest.mark.parametrize("malformed", ["case", "result"])
def test_unvalidated_model_copies_cannot_change_denominator_identity(
    malformed: str,
) -> None:
    """Duplicate cases and within-case result IDs fail instead of being coalesced."""
    workload = results(timed(1), (("r1",),))
    if malformed == "case":
        workload = workload.model_copy(update={"cases": workload.cases * 2})
    else:
        workload = results(workload, (("r1", "r1"),))
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_reportable_cost(
            workload,
            Decimal(10),
            service_scope="static_projection",
        )


@pytest.mark.parametrize(
    ("ids", "count", "state", "ratio"),
    [
        ((None, None), None, "unknown", None),
        ((("r1",), None), None, "unknown", None),
        (((), ()), 0, "zero", None),
        ((("shared",), ("shared",)), 1, "positive", Fraction(79, 2)),
        ((("r1", "r2"), ("r2", "r3")), 3, "positive", Fraction(79, 6)),
    ],
)
def test_static_declared_result_counts_do_not_replace_demand(
    tmp_path: Path,
    ids: tuple[tuple[str, ...] | None, ...],
    count: int | None,
    state: str,
    ratio: Fraction | None,
) -> None:
    """Unknown, zero and shared IDs have different meanings with unchanged costs."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    workload = results(timed(2), ids)
    batch = policy().model_copy(update={"entity_kind": "requested_tests"})
    value = calculate_static_batch_cost(workload, batch, pricing, context)
    summary = value.reportable_cost
    if summary is None:
        raise AssertionError
    require_equal(value.total_cost, Decimal("39.5"))
    require_equal(value.unit_cost, Fraction(79, 4))
    require_equal(summary.declared_result_count, count)
    require_equal(summary.count_state, state)
    require_equal(summary.service_scope, "static_projection")
    require_equal(summary.unit_cost_per_declared_reportable_result, ratio)
    require_equal(summary.selected_cost_known, expected=True)
    require_equal(summary.format_version, "reportable-cost-v1")


def test_library_and_report_counts_are_independent(tmp_path: Path) -> None:
    """One shared library and two declared reports retain distinct ratios."""
    pricing, context = batch_inputs(tmp_path)
    workload = results(timed(2), (("r1",), ("r2",)))
    workload = workload.model_copy(
        update={
            "cases": tuple(
                c.model_copy(update={"library_ids": ("shared-library",)})
                for c in workload.cases
            ),
        },
    )
    value = calculate_static_batch_cost(workload, policy(), pricing, context)
    summary = value.reportable_cost
    if summary is None:
        raise AssertionError
    require_equal(value.demand_count, 1)
    require_equal(value.unit_cost, Fraction(75, 2))
    require_equal(summary.declared_result_count, 2)
    require_equal(summary.unit_cost_per_declared_reportable_result, Fraction(75, 4))


def test_zero_demand_keeps_fixed_cost_without_a_report_ratio(tmp_path: Path) -> None:
    """The empty cohort has a known zero result count and undefined unit cost."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    batch = policy().model_copy(update={"entity_kind": "requested_tests"})
    value = calculate_static_batch_cost(timed(0), batch, pricing, context)
    summary = value.reportable_cost
    if summary is None:
        raise AssertionError
    require_equal(value.total_cost, Decimal(10))
    require_equal(value.idle_cost, Decimal(10))
    require_equal(summary.declared_result_count, 0)
    require_equal(summary.unit_cost_per_declared_reportable_result, None)


def test_partial_dynamic_cost_cannot_use_whole_cohort_report_denominator(
    tmp_path: Path,
) -> None:
    """A shared result ID does not make an unserved case disappear."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    workload = results(timed(2), (("shared",), ("shared",)))
    workload = workload.model_copy(
        update={
            "cases": (
                workload.cases[0],
                workload.cases[1].model_copy(update={"arrival_seconds": Decimal(4)}),
            ),
        },
    )
    selected = dynamic().model_copy(
        update={
            "windows": (
                AvailabilityWindow(start_seconds=Decimal(0), end_seconds=Decimal(3)),
            ),
        },
    )
    value = calculate_dynamic_batch_cost(workload, selected, pricing, context)
    summary = value.cost.reportable_cost
    if summary is None:
        raise AssertionError
    require_equal(value.cost_state, "partial_workload")
    require_equal(value.schedule.unserved_case_ids, ("c1",))
    require_equal(summary.declared_result_count, 1)
    require_equal(summary.service_scope, "partial_modeled_workload")
    require_equal(summary.unit_cost_per_declared_reportable_result, None)


def test_complete_but_late_cost_keeps_feasibility_separate(tmp_path: Path) -> None:
    """A descriptive ratio does not claim that the TAT requirement was met."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    workload = results(timed(2), (("shared",), ("shared",)))
    selected = dynamic().model_copy(update={"turnaround_limit_seconds": Decimal(2)})
    value = calculate_dynamic_batch_cost(workload, selected, pricing, context)
    summary = value.cost.reportable_cost
    if summary is None:
        raise AssertionError
    require_equal(value.schedule.feasibility, "infeasible")
    require_equal(summary.service_scope, "complete_modeled_workload")
    require_equal(summary.unit_cost_per_declared_reportable_result, Fraction(79, 2))


@pytest.mark.parametrize("shortage", [False, True])
def test_workflow_ratio_requires_complete_service_and_materials(
    tmp_path: Path,
    *,
    shortage: bool,
) -> None:
    """Declared-component cost cannot become a whole-service ratio on shortage."""
    inputs = cost_inputs(tmp_path)
    workflow = inputs.inventory.workflow
    workload = results(workflow.workload, (("shared",), ("shared",)))
    inventory = replace(inputs.inventory, workflow=replace(workflow, workload=workload))
    if shortage:
        stock = json.loads(inventory.stock_payload)
        for pack in stock["packs"]:
            pack["arrived_seconds"] = "100"
        inventory = restock(inventory, stock)
    value = calculate_workflow_cost(replace(inputs, inventory=inventory))
    summary = value.reportable_cost
    if summary is None:
        raise AssertionError
    require_equal(summary.declared_result_count, 1)
    require_equal(
        summary.service_scope,
        "partial_modeled_workload" if shortage else "complete_modeled_workload",
    )
    require_equal(
        summary.unit_cost_per_declared_reportable_result,
        None if shortage else Fraction(33),
    )
    require_equal(value.eligible_for_comparison, expected=not shortage)
