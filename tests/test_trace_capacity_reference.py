# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Exact reference allocation preserves sources, failures and unknowns."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
lazy from pathlib import Path

import pytest
from pydantic import ValidationError

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    CoreHourPricing,
)
from genomics_microcosting.provenance_ledger import (
    Parameter,
    ParameterQualification,
    ParameterSet,
    QualificationLedger,
    SourceRecord,
    SourceValidity,
)
from genomics_microcosting.trace_capacity_reference import (
    ReferenceCapacityWindow,
    TraceCapacityReferenceInputs,
    allocate_trace_capacity_reference,
)
from genomics_microcosting.trace_registry import TraceExport
from tests import checks
from tests.test_execution_reconciliation import bindings, exports
from tests.test_nextflow_export_profile import HEADER, probe_context


def reference_inputs(
    tmp_path: Path,
    *,
    quantity: str = "2",
    rate: str = "2",
    share: str = "1",
) -> TraceCapacityReferenceInputs:
    """Provide independent synthetic rates and exact existing trace fixtures."""
    parameters: list[Parameter] = []
    qualifications: list[ParameterQualification] = []
    validity: list[SourceValidity] = []
    snapshots: dict[str, Path] = {}
    day = date(2026, 11, 7)
    for name, raw, unit in [
        ("quantity", quantity, "core_h"),
        ("rate", rate, "AUD/core_h"),
        ("share", share, "fraction"),
    ]:
        path = tmp_path / (name + ".txt")
        path.write_text(raw + "\n", encoding="utf-8")
        digest = sha256(path.read_bytes()).hexdigest()
        source = SourceRecord(
            source_id=name,
            sha256=digest,
            edition="synthetic",
            locator="line 1",
            limitations="Synthetic declared reference only",
        )
        parameter = Parameter(
            parameter_id=name,
            raw_value=raw,
            derived_value=raw,
            unit=unit,
            source_sha256=digest,
            source_locator="line 1",
            transformation="identity",
            uncertainty="synthetic",
            status="assumed",
        )
        parameters.append(parameter)
        qualifications.append(
            ParameterQualification(
                parameter=parameter,
                source=source,
                exact_support=raw,
                dimensional_basis=unit,
                applicability="Only this toy reference",
                qualification="qualified",
                blockers=(),
            ),
        )
        validity.append(
            SourceValidity(
                source=source,
                retrieved=day,
                effective_from=day,
                effective_until=day,
                date_basis="Synthetic observation",
                applicability_kind="observation",
            ),
        )
        snapshots[name] = path
    context = ComputeCostContext(
        QualificationLedger(
            parameter_set=ParameterSet(
                version_id="ref1",
                workbook_sha256="a" * 64,
                parameters=tuple(parameters),
            ),
            qualifications=tuple(qualifications),
        ),
        snapshots,
        tuple(validity),
        day,
    )
    pricing = CoreHourPricing.model_validate(
        {
            "function_version": "compute-core-hour-cost-v1",
            "workload_id": "reference-period",
            "currency": "AUD",
            "price_year": 2026,
            "tax_basis": "exclusive",
            "bill_parameter_id": None,
            "meters": [
                {
                    "meter_id": "bundle",
                    "quantity_parameter_id": "quantity",
                    "rate_parameter_id": "rate",
                    "allocation_parameter_id": "share",
                    "unit": "core_h",
                    "usage_basis": "requested",
                    "price_basis": "requested",
                },
            ],
        },
    )
    window = ReferenceCapacityWindow.model_validate(
        {
            "format_version": "trace-capacity-reference-v1",
            "reference_period_id": "reference-period",
            "native_workload_id": "t5-nf-synthetic-v1",
            "reference_vcpus": 2,
            "reference_memory_bytes": 1024**3,
            "horizon_seconds": "3600",
            "reference_vcpus_per_native_slot": "1",
            "mapping_assumption": "Toy accounting mapping; not performance",
            "bundle_allocation_assumption": "Toy equal-core bundle allocation",
            "scope_limit": "Synthetic reference only, no actual cost or bill",
        },
    )
    return TraceCapacityReferenceInputs(
        exports(),
        bindings(),
        window,
        pricing,
        context,
    )


def changed_exports(
    inputs: TraceCapacityReferenceInputs,
    before: bytes,
    after: bytes,
    *,
    original_only: bool = False,
) -> TraceCapacityReferenceInputs:
    """Rebind altered test bytes while retaining exact row/link coverage."""
    updated: list[TraceExport] = []
    by_old_hash: dict[str, str] = {}
    for index, export in enumerate(inputs.exports):
        raw = (
            export.payload
            if original_only and index
            else export.payload.replace(before, after)
        )
        context = export.context.model_copy(
            update={
                "source_sha256": sha256(raw).hexdigest(),
            },
        )
        updated.append(TraceExport(raw, context))
        by_old_hash[export.context.source_sha256] = context.source_sha256
    links = tuple(
        b.model_copy(
            update={
                "source_sha256": by_old_hash[b.source_sha256],
            },
        )
        for b in inputs.bindings
    )
    return replace(inputs, exports=tuple(updated), bindings=links)


def test_exact_native_share_and_reference_residual(tmp_path: Path) -> None:
    """Three original executions include failure without cached duplication."""
    inputs = reference_inputs(tmp_path)
    result = allocate_trace_capacity_reference(inputs)
    checks.require_equal(len(result.lines), 3)
    checks.require_equal(len(result.executions.observations), 5)
    checks.require_equal(
        result.requested_reference_vcpu_seconds,
        Fraction(2077, 1000),
    )
    checks.require_equal(result.share, Fraction(2077, 7_200_000))
    checks.require_equal(
        result.selected_reference_cost,
        Fraction(2077, 1_800_000),
    )
    checks.require_equal(
        result.unallocated_reference_cost,
        Fraction(7_197_923, 1_800_000),
    )
    checks.require_equal(result.period_cost.modeled_total, Decimal(4))
    checks.require_equal(result.actual_bill, None)
    checks.require_equal(result.full_workload_cost, None)
    checks.require_equal(result.temporal_feasibility, "not_assessed")
    checks.require_equal(result.cost_scope, "reference_bundle_only")
    checks.require_equal(allocate_trace_capacity_reference(inputs), result)
    reordered = replace(
        inputs,
        exports=tuple(reversed(inputs.exports)),
        bindings=tuple(reversed(inputs.bindings)),
    )
    checks.require_equal(allocate_trace_capacity_reference(reordered), result)


@pytest.mark.parametrize("field", ["realtime", "cpus"])
def test_cache_cannot_fill_missing_original_quantities(
    tmp_path: Path,
    field: str,
) -> None:
    """Unknown original time or slots suppress the whole allocation/residual."""
    inputs = reference_inputs(tmp_path)
    if field == "realtime":
        inputs = changed_exports(
            inputs,
            b"1107\t1030",
            b"1107\t-",
            original_only=True,
        )
    else:
        inputs = changed_exports(
            inputs,
            b"COMPLETED\t1\t1\t67108864",
            b"COMPLETED\t1\t-\t67108864",
            original_only=True,
        )
    result = allocate_trace_capacity_reference(inputs)
    checks.require_equal(result.quantity_state, "incomplete")
    checks.require_equal(result.missing_quantity_execution_ids, ("success",))
    checks.require_equal(
        result.known_requested_reference_vcpu_seconds,
        Fraction(1047, 1000),
    )
    checks.require_equal(
        result.known_subtotal_reference_cost,
        Fraction(1047, 1_800_000),
    )
    for value in [
        result.share,
        result.selected_reference_cost,
        result.unallocated_reference_cost,
        result.requested_reference_vcpu_seconds,
    ]:
        checks.require_equal(value, None)


def test_unknown_original_memory_does_not_become_zero(tmp_path: Path) -> None:
    """Unknown shape remains unassessed alongside a known CPU-slot proxy."""
    inputs = changed_exports(
        reference_inputs(tmp_path),
        b"67108864\t-",
        b"-\t-",
        original_only=True,
    )
    result = allocate_trace_capacity_reference(inputs)
    checks.require_equal(result.per_task_shape, "unknown")
    checks.require_equal(result.quantity_state, "complete")
    checks.require_equal(result.temporal_feasibility, "not_assessed")
    checks.require_equal(
        result.requested_reference_vcpu_seconds,
        Fraction(2077, 1000),
    )


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (b"\t1\t67108864\t", b"\t3\t67108864\t"),
        (b"\t1\t67108864\t", b"\t0\t67108864\t"),
        (b"67108864", b"2147483648"),
    ],
)
def test_incompatible_original_request_shape_rejects(
    tmp_path: Path,
    before: bytes,
    after: bytes,
) -> None:
    """A plausible aggregate share cannot excuse a per-task shape violation."""
    inputs = changed_exports(reference_inputs(tmp_path), before, after)
    with pytest.raises(ValueError, match="reference task shape"):
        allocate_trace_capacity_reference(inputs)


def test_aggregate_request_exceeding_period_capacity_rejects(
    tmp_path: Path,
) -> None:
    """Reject a negative residual without changing the sourced price period."""
    inputs = reference_inputs(tmp_path, quantity="0.0002")
    inputs = replace(
        inputs,
        window=inputs.window.model_copy(
            update={
                "horizon_seconds": Decimal("0.36"),
            },
        ),
    )
    with pytest.raises(ValueError, match="subtotal exceeds"):
        allocate_trace_capacity_reference(inputs)


@pytest.mark.parametrize("rate", ["2", "0"])
def test_partial_period_selection_rejects_even_at_zero_price(
    tmp_path: Path,
    rate: str,
) -> None:
    """A zero total cannot hide a half-period selection behind cost equality."""
    inputs = reference_inputs(tmp_path, rate=rate, share="0.5")
    with pytest.raises(ValueError, match="whole-period selection"):
        allocate_trace_capacity_reference(inputs)


def test_empty_export_retains_unallocated_reference_price(
    tmp_path: Path,
) -> None:
    """A documented empty scope is distinct from an absent source context."""
    inputs = reference_inputs(tmp_path)
    export = TraceExport(HEADER, probe_context(HEADER, "empty"))
    result = allocate_trace_capacity_reference(
        replace(inputs, exports=(export,), bindings=()),
    )
    checks.require_equal(result.quantity_state, "complete")
    checks.require_equal(result.selected_reference_cost, Fraction(0))
    checks.require_equal(result.unallocated_reference_cost, Fraction(4))
    with pytest.raises(ValueError, match="context differs or is absent"):
        allocate_trace_capacity_reference(
            replace(inputs, exports=(), bindings=()),
        )


def test_explicit_mapping_changes_only_conditional_allocation(
    tmp_path: Path,
) -> None:
    """Keep CPU-slot economic mapping explicit."""
    inputs = reference_inputs(tmp_path)
    first = allocate_trace_capacity_reference(inputs)
    changed = replace(
        inputs,
        window=inputs.window.model_copy(
            update={
                "reference_vcpus_per_native_slot": Decimal("0.5"),
            },
        ),
    )
    result = allocate_trace_capacity_reference(changed)
    checks.require_equal(result.period_cost, first.period_cost)
    checks.require_equal(result.share, Fraction(2077, 14_400_000))
    if result.input_sha256 == first.input_sha256:
        pytest.fail("Changed economic mapping lost its input identity")


@pytest.mark.parametrize(
    "kind",
    ["workload", "period", "quantity", "bill", "basis", "date", "currency"],
)
def test_frame_and_source_checks_are_preserved(
    tmp_path: Path,
    kind: str,
) -> None:
    """Reject source and frame errors before allocation."""
    inputs = reference_inputs(tmp_path)
    if kind == "workload":
        inputs = replace(
            inputs,
            window=inputs.window.model_copy(
                update={
                    "native_workload_id": "other",
                },
            ),
        )
    elif kind == "period":
        inputs = replace(
            inputs,
            window=inputs.window.model_copy(
                update={
                    "reference_period_id": "other",
                },
            ),
        )
    elif kind == "quantity":
        inputs = replace(
            inputs,
            window=inputs.window.model_copy(
                update={
                    "horizon_seconds": Decimal(1800),
                },
            ),
        )
    elif kind == "bill":
        inputs = replace(
            inputs,
            pricing=inputs.pricing.model_copy(
                update={
                    "bill_parameter_id": "bill",
                },
            ),
        )
    elif kind == "basis":
        meters = tuple(
            m.model_copy(
                update={"usage_basis": "measured", "price_basis": "measured"},
            )
            for m in inputs.pricing.meters
        )
        inputs = replace(
            inputs,
            pricing=inputs.pricing.model_copy(
                update={
                    "meters": meters,
                },
            ),
        )
    elif kind == "date":
        inputs = replace(
            inputs,
            price_context=replace(
                inputs.price_context,
                costing_date=inputs.price_context.costing_date + timedelta(days=1),
            ),
        )
    else:
        inputs = replace(
            inputs,
            pricing=inputs.pricing.model_copy(
                update={
                    "currency": "USD",
                },
            ),
        )
    expected = {
        "workload": "workload context",
        "period": "requested-basis",
        "quantity": "quantity",
        "bill": "requested-basis",
        "basis": "requested-basis",
        "date": "costing date",
        "currency": "unit differs",
    }
    with pytest.raises(ValueError, match=expected[kind]):
        allocate_trace_capacity_reference(inputs)


def test_price_tampering_is_rechecked(tmp_path: Path) -> None:
    """A prior valid capacity result cannot replace current numeric evidence."""
    inputs = reference_inputs(tmp_path)
    (tmp_path / "rate.txt").write_text("3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        allocate_trace_capacity_reference(inputs)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reference_vcpus", True),
        ("reference_memory_bytes", 0),
        ("horizon_seconds", "1e-99999"),
        ("reference_vcpus_per_native_slot", "1e99999"),
    ],
)
def test_declared_capacity_profile_is_bounded(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    """Bound rational construction before any native-cost arithmetic."""
    inputs = reference_inputs(tmp_path)
    with pytest.raises(ValidationError):
        allocate_trace_capacity_reference(
            replace(
                inputs,
                window=inputs.window.model_copy(update={field: value}),
            ),
        )


def test_reported_zero_time_is_known_without_measured_cpu_claim(
    tmp_path: Path,
) -> None:
    """A zero task counter stays distinct from a missing original counter."""
    inputs = changed_exports(
        reference_inputs(tmp_path),
        b"1107\t1030",
        b"1107\t0",
    )
    result = allocate_trace_capacity_reference(inputs)
    checks.require_equal(result.quantity_state, "complete")
    checks.require_equal(
        result.requested_reference_vcpu_seconds,
        Fraction(1047, 1000),
    )
    checks.require_equal(
        result.selected_reference_cost,
        Fraction(1047, 1_800_000),
    )
    checks.require_equal(result.actual_bill, None)


def test_zero_reference_price_does_not_resolve_missing_quantity(
    tmp_path: Path,
) -> None:
    """Even a zero reference price cannot invent a complete requested share."""
    inputs = changed_exports(
        reference_inputs(tmp_path, rate="0"),
        b"1107\t1030",
        b"1107\t-",
        original_only=True,
    )
    result = allocate_trace_capacity_reference(inputs)
    checks.require_equal(result.period_cost.modeled_total, Decimal(0))
    checks.require_equal(result.known_subtotal_reference_cost, Fraction(0))
    checks.require_equal(result.selected_reference_cost, None)
    checks.require_equal(result.unallocated_reference_cost, None)


def test_reference_amount_conversion_has_bounded_exponents(
    tmp_path: Path,
) -> None:
    """Bound source-checked amounts before rational conversion."""
    inputs = reference_inputs(tmp_path, rate="1e1000")
    with pytest.raises(ValueError, match="finite profile"):
        allocate_trace_capacity_reference(inputs)
