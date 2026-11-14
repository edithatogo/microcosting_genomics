# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check explicit compute evidence changes the finite batch objective."""

from dataclasses import replace
from decimal import Decimal
from typing import Literal, TypedDict, cast
lazy from pathlib import Path

import pytest

from genomics_microcosting.batch_compute_search import (
    ComponentAssignment,
    ComputePolicyGrid,
    ComputePolicyInput,
    CostBoundary,
    enumerate_compute_batch_policies,
)
from genomics_microcosting.batch_policy_search import enumerate_batch_policies
from tests import checks
from tests.test_compute_cost import inputs
from tests.test_core_hour_cost import hourly_inputs
from tests.test_dynamic_batch import dynamic, timed
from tests.test_static_batch_cost import batch_inputs


class SearchGrid(TypedDict):
    """Keep the two policy grid axes distinctly typed."""

    payload_limits: tuple[int, ...]
    max_wait_seconds: tuple[Decimal, ...]


def boundary() -> CostBoundary:
    """Declare synthetic nonoverlapping component names, not empirical proof."""
    return CostBoundary(
        assignments=(
            *(
                ComponentAssignment(
                    domain="batch",
                    input_id=name,
                    component_ids=(f"wetlab-{name}",),
                )
                for name in ("quantity", "rate", "share", "bill")
            ),
            ComponentAssignment(
                domain="compute",
                input_id="cpu",
                component_ids=("compute-cpu",),
            ),
        ),
        assumption_basis="synthetic resource boundary only",
    )


@pytest.mark.parametrize("unit", ["seconds", "hours"])
def test_compute_cost_changes_frontier_and_missing_data_stays_unknown(
    tmp_path: Path,
    unit: Literal["seconds", "hours"],
) -> None:
    """A cheaper wet-lab policy becomes dominated after its explicit compute cost."""
    bp = tmp_path / "batch"
    bp.mkdir()
    pricing, context = batch_inputs(bp, "requested_tests")
    w = timed(2)
    w = w.model_copy(
        update={
            "cases": (
                w.cases[0],
                w.cases[1].model_copy(update={"arrival_seconds": Decimal(4)}),
            ),
        },
    )
    grid: SearchGrid = {
        "payload_limits": (2,),
        "max_wait_seconds": (Decimal(0), Decimal(4)),
    }
    batch = enumerate_batch_policies(w, dynamic(), pricing, context, **grid)
    bindings: dict[str, ComputePolicyInput] = {}
    for i, quantity in enumerate(("5", "100")):
        folder = tmp_path / str(i)
        folder.mkdir()
        cp, cc = (hourly_inputs if unit == "hours" else inputs)(folder, quantity)
        cp = cp.model_copy(update={"workload_id": w.workload_id})
        bindings[batch.points[i].result.schedule.input_sha256] = ComputePolicyInput(
            cp,
            cc,
        )
    result = enumerate_compute_batch_policies(
        w,
        dynamic(),
        pricing,
        context,
        boundary(),
        compute_inputs=bindings,
        **grid,
    )
    checks.require_equal(result.state, "priced")
    checks.require_equal(result.pareto_indices, (0,))
    checks.require_equal(
        tuple(p.total_cost for p in result.points),
        (Decimal(70), Decimal("139.5")),
    )
    compute = result.points[1].compute
    if compute is None:
        raise AssertionError
    checks.require_equal(compute.unallocated_cost, Decimal(100))
    checks.require_equal(compute.bill_residual, Decimal(-175))
    missing = dict(bindings)
    del missing[batch.points[1].result.schedule.input_sha256]
    partial = enumerate_compute_batch_policies(
        w,
        dynamic(),
        pricing,
        context,
        boundary(),
        compute_inputs=missing,
        **grid,
    )
    checks.require_equal(partial.state, "incomplete_compute_data")
    checks.require_equal(partial.points[1].total_cost, None)
    checks.require_equal(partial.points[1].cost_state, "missing_compute")
    checks.require_equal(partial.pareto_indices, (0,))
    for field, value in (
        ("currency", "USD"),
        ("price_year", 2025),
        ("tax_basis", "exclusive"),
        ("workload_id", "wrong"),
    ):
        changed = dict(bindings)
        key = batch.points[0].result.schedule.input_sha256
        changed[key] = replace(
            bindings[key],
            pricing=bindings[key].pricing.model_copy(
                update={field: value},
            ),
        )
        with pytest.raises(ValueError, match="basis"):
            enumerate_compute_batch_policies(
                w,
                dynamic(),
                pricing,
                context,
                boundary(),
                compute_inputs=changed,
                **grid,
            )
    bindings["a" * 64] = next(iter(bindings.values()))
    with pytest.raises(ValueError, match="unknown schedule"):
        enumerate_compute_batch_policies(
            w,
            dynamic(),
            pricing,
            context,
            boundary(),
            compute_inputs=bindings,
            **grid,
        )


def test_cost_boundary_rejects_overlap_and_incomplete_coverage(tmp_path: Path) -> None:
    """Explicit component names cannot overlap or omit selected cost drivers."""
    with pytest.raises(ValueError, match="overlap"):
        CostBoundary(
            assignments=(
                ComponentAssignment(
                    domain="batch",
                    input_id="quantity",
                    component_ids=("same",),
                ),
                ComponentAssignment(
                    domain="compute",
                    input_id="cpu",
                    component_ids=("same",),
                ),
            ),
            assumption_basis="synthetic",
        )
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    incomplete = boundary().model_copy(
        update={"assignments": boundary().assignments[1:]},
    )
    with pytest.raises(ValueError, match="coverage"):
        enumerate_compute_batch_policies(
            timed(1),
            dynamic(),
            pricing,
            context,
            incomplete,
            compute_inputs={},
            payload_limits=(1,),
            max_wait_seconds=(Decimal(0),),
        )


def test_partial_service_and_empty_demand_keep_distinct_states(tmp_path: Path) -> None:
    """No compute evidence cannot masquerade as zero cost or complete service."""
    folder = tmp_path / "batch"
    folder.mkdir()
    pricing, context = batch_inputs(folder, "requested_tests")
    policy = dynamic().model_copy(update={"windows": ()})
    partial = enumerate_compute_batch_policies(
        timed(1),
        policy,
        pricing,
        context,
        boundary(),
        compute_inputs={},
        payload_limits=(1,),
        max_wait_seconds=(Decimal(0),),
    )
    checks.require_equal(partial.state, "infeasible")
    checks.require_equal(partial.points[0].cost_state, "partial_batch")
    checks.require_equal(partial.pareto_indices, ())
    cp, cc = inputs(tmp_path)
    cp = cp.model_copy(update={"workload_id": "w1"})
    key = partial.points[0].batch.result.schedule.input_sha256
    with pytest.raises(ValueError, match="partial batch"):
        enumerate_compute_batch_policies(
            timed(1),
            policy,
            pricing,
            context,
            boundary(),
            compute_inputs={key: ComputePolicyInput(cp, cc)},
            payload_limits=(1,),
            max_wait_seconds=(Decimal(0),),
        )
    idle = enumerate_compute_batch_policies(
        timed(0),
        dynamic(),
        pricing,
        context,
        boundary(),
        compute_inputs={},
        payload_limits=(1,),
        max_wait_seconds=(Decimal(0),),
    )
    checks.require_equal(idle.state, "no_demand")
    checks.require_equal(idle.points[0].total_cost, None)


@pytest.mark.parametrize("unit", ["seconds", "hours"])
def test_integration_rechecks_sources_and_compute_boundary(
    tmp_path: Path,
    unit: Literal["seconds", "hours"],
) -> None:
    """Bindings must retain original bytes and exact meter scope at execution."""
    folder = tmp_path / "batch"
    folder.mkdir()
    pricing, context = batch_inputs(folder, "requested_tests")
    cp, cc = (hourly_inputs if unit == "hours" else inputs)(tmp_path)
    cp = cp.model_copy(update={"workload_id": "w1"})
    w = timed(1)
    batch = enumerate_batch_policies(
        w,
        dynamic(),
        pricing,
        context,
        payload_limits=(1,),
        max_wait_seconds=(Decimal(0),),
    )
    key = batch.points[0].result.schedule.input_sha256
    bindings = {key: ComputePolicyInput(cp, cc)}
    b = boundary()
    wrong = b.model_copy(
        update={
            "assignments": (
                *b.assignments[:-1],
                b.assignments[-1].model_copy(update={"input_id": "wrong"}),
            ),
        },
    )
    with pytest.raises(ValueError, match="coverage"):
        enumerate_compute_batch_policies(
            w,
            dynamic(),
            pricing,
            context,
            wrong,
            compute_inputs=bindings,
            payload_limits=(1,),
            max_wait_seconds=(Decimal(0),),
        )
    original = enumerate_compute_batch_policies(
        w,
        dynamic(),
        pricing,
        context,
        b,
        compute_inputs=bindings,
        payload_limits=(1,),
        max_wait_seconds=(Decimal(0),),
    )
    repeated = enumerate_compute_batch_policies(
        w,
        dynamic(),
        pricing,
        context,
        b,
        compute_inputs=bindings,
        payload_limits=(1,),
        max_wait_seconds=(Decimal(0),),
    )
    checks.require_equal(original, repeated)
    cc.snapshots["quantity"].write_text("11\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        enumerate_compute_batch_policies(
            w,
            dynamic(),
            pricing,
            context,
            b,
            compute_inputs=bindings,
            payload_limits=(1,),
            max_wait_seconds=(Decimal(0),),
        )


def test_compute_grid_rejects_invalid_runtime_keyword_names(tmp_path: Path) -> None:
    """Reject untyped callers with an unknown compute evidence argument."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    options = cast(
        "ComputePolicyGrid",
        {"payload_limits": (1,), "max_wait_seconds": (), "compute_inputs_typo": {}},
    )
    with pytest.raises(TypeError, match="Expected payload_limits"):
        enumerate_compute_batch_policies(
            timed(1),
            dynamic(),
            pricing,
            context,
            boundary(),
            **options,
        )
