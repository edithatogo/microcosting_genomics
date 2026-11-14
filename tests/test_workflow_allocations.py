# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Requested resource allocations preserve exact units and legacy cost scope."""

import json
from dataclasses import replace
from datetime import date
from fractions import Fraction
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.compute_cost import ComputeCostContext
from genomics_microcosting.provenance_ledger import (
    Parameter,
    ParameterQualification,
    ParameterSet,
    QualificationLedger,
    SourceRecord,
    SourceValidity,
)
from genomics_microcosting.workflow_allocations import (
    RequestedAllocationPricing,
    WorkflowAllocationInputs,
    allocation_workload_sha256,
    calculate_allocated_workflow_cost,
)
from genomics_microcosting.workflow_cost import calculate_workflow_cost
from tests.checks import require_equal
from tests.test_inventory_ledger import restock
from tests.test_workflow_cost import cost_inputs


def allocation_inputs(
    tmp_path: Path,
    *,
    numerator: str = "1",
    denominator: str = "3",
    rate: str = "7",
    units: tuple[str, str] = ("reaction", "reaction"),
) -> WorkflowAllocationInputs:
    """Provide declared synthetic fractional resource allocations."""
    numerator_unit, resource_unit = units
    base = cost_inputs(tmp_path / "base")
    workload = base.inventory.workflow.workload
    records: list[Parameter] = []
    qualifications: list[ParameterQualification] = []
    validity: list[SourceValidity] = []
    snapshots: dict[str, Path] = {}
    for name, raw, unit in [
        ("num", numerator, numerator_unit),
        ("den", denominator, "declared_requested_test"),
        ("rate", rate, f"AUD/{resource_unit}"),
    ]:
        path = tmp_path / f"{name}.txt"
        path.write_text(raw + "\n", encoding="utf-8")
        digest = sha256(path.read_bytes()).hexdigest()
        source = SourceRecord(
            source_id=name,
            sha256=digest,
            edition="synthetic-v1",
            locator="line 1",
            limitations="No empirical applicability",
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
            status="reported",
        )
        records.append(parameter)
        qualifications.append(
            ParameterQualification(
                parameter=parameter,
                source=source,
                exact_support=raw,
                dimensional_basis=unit,
                applicability="Synthetic declared cases",
                qualification="qualified",
                blockers=(),
            ),
        )
        validity.append(
            SourceValidity(
                source=source,
                retrieved=date(2026, 11, 7),
                effective_from=date(2026, 1, 1),
                effective_until=date(2026, 12, 31),
                date_basis="synthetic",
            ),
        )
        snapshots[name] = path
    context = ComputeCostContext(
        QualificationLedger(
            parameter_set=ParameterSet(
                version_id=workload.parameter_version_id,
                workbook_sha256="c" * 64,
                parameters=tuple(records),
            ),
            qualifications=tuple(qualifications),
        ),
        snapshots,
        tuple(validity),
        date(2026, 11, 7),
    )
    cases = [c.case_id for c in workload.cases]
    pricing = RequestedAllocationPricing.model_validate(
        {
            "format_version": "requested-allocations-v1",
            "workload_sha256": allocation_workload_sha256(workload),
            "currency": "AUD",
            "price_year": 2026,
            "tax_basis": "exclusive",
            "resources": [
                {
                    "resource_id": "extra",
                    "resource_unit": resource_unit,
                    "rate_parameter_id": "rate",
                    "case_ids": cases,
                    "component_ids": ["separate-resource-allocation"],
                },
            ],
            "quantities": [
                {
                    "resource_id": "extra",
                    "case_id": c,
                    "numerator_parameter_id": "num",
                    "denominator_parameter_id": "den",
                }
                for c in cases
            ],
            "assumption_basis": "Synthetic disjoint requested-case allocation",
            "scope_limit": "No observed physical consumption or complete costs",
            "allocation_basis": "declared_requested_cases",
        },
    )
    return WorkflowAllocationInputs(base, pricing, context)


def test_exact_fraction_and_recomputed_legacy_cost(tmp_path: Path) -> None:
    """One-third allocations do not invent runtime or material issues."""
    inputs = allocation_inputs(tmp_path)
    before = calculate_workflow_cost(inputs.workflow)
    result = calculate_allocated_workflow_cost(inputs)
    require_equal(result.base_cost, before)
    require_equal(result.lines[0].quantity, Fraction(1, 3))
    require_equal(result.selected_allocation_cost, Fraction(14, 3))
    require_equal(result.total_selected_cost, Fraction(113, 3))
    require_equal(result.unit_cost_per_requested_test, Fraction(113, 6))
    require_equal(result.full_workload_cost, None)
    require_equal(result.allocation_physical_feasibility, "not_assessed")
    require_equal(calculate_allocated_workflow_cost(inputs), result)


@pytest.mark.parametrize(
    ("key", "value", "error"),
    [
        ("currency", "USD", "economic frame"),
        ("price_year", 2023, "economic frame"),
        ("tax_basis", "inclusive", "economic frame"),
        ("workload_sha256", "f" * 64, "workload identity"),
        ("allocation_basis", "completed_cases", "declared_requested_cases"),
    ],
)
def test_selection_frame_rejects_drift(
    tmp_path: Path,
    key: str,
    value: object,
    error: str,
) -> None:
    """Allocation selection cannot silently change its source/workload frame."""
    inputs = allocation_inputs(tmp_path)
    data = inputs.pricing.model_dump(mode="json")
    data[key] = value
    with pytest.raises(ValueError, match=error):
        calculate_allocated_workflow_cost(
            replace(
                inputs,
                pricing=RequestedAllocationPricing.model_validate(data),
            ),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_quantity",
        "extra_quantity",
        "duplicate_resource",
        "duplicate_component",
        "duplicate_case",
        "unknown_case",
        "overlap",
    ],
)
def test_scope_and_component_guards(tmp_path: Path, mutation: str) -> None:
    """Declared coverage and nonoverlap must hold before pricing."""
    inputs = allocation_inputs(tmp_path)
    data = inputs.pricing.model_dump(mode="json")
    if mutation == "missing_quantity":
        data["quantities"].pop()
    elif mutation == "extra_quantity":
        data["quantities"].append(data["quantities"][0])
    elif mutation == "duplicate_resource":
        data["resources"].append(data["resources"][0])
    elif mutation == "duplicate_component":
        data["resources"][0]["component_ids"] *= 2
    elif mutation == "duplicate_case":
        data["resources"][0]["case_ids"] *= 2
    elif mutation == "unknown_case":
        data["resources"][0]["case_ids"][0] = "unknown"
        data["quantities"][0]["case_id"] = "unknown"
    else:
        data["resources"][0]["component_ids"] = ["staff-time"]
    with pytest.raises(ValueError, match=r"Duplicate|cover|unknown|overlaps"):
        calculate_allocated_workflow_cost(
            replace(
                inputs,
                pricing=RequestedAllocationPricing.model_validate(data),
            ),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("denominator", "0"),
        ("denominator", "1.5"),
        ("numerator", "-1"),
        ("rate", "-1"),
        ("numerator", "1e-129"),
        ("rate", "1e129"),
    ],
)
def test_numeric_profile_and_denominator(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    """No negative charges, fractional cases, zero division or huge ratios."""
    with pytest.raises(ValueError, match="Allocation"):
        calculate_allocated_workflow_cost(
            allocation_inputs(
                tmp_path,
                numerator=value if field == "numerator" else "1",
                denominator=value if field == "denominator" else "3",
                rate=value if field == "rate" else "7",
            ),
        )


def test_quantity_unit_is_checked(tmp_path: Path) -> None:
    """Matching scalar numbers do not permit implicit unit conversions."""
    inputs = allocation_inputs(tmp_path, units=("staff_hour", "reaction"))
    with pytest.raises(ValueError, match="unit mismatch"):
        calculate_allocated_workflow_cost(inputs)


@pytest.mark.parametrize(
    "mutation",
    ["bytes", "expired", "version", "baseline", "unqualified"],
)
def test_source_integrity_validity_and_identity(
    tmp_path: Path,
    mutation: str,
) -> None:
    """The numeric source verifier remains required for extra allocations."""
    inputs = allocation_inputs(tmp_path)
    if mutation == "bytes":
        inputs.context.snapshots["num"].write_text("2\n", encoding="utf-8")
    elif mutation == "expired":
        expired = inputs.context.validity[0].model_copy(
            update={"effective_until": date(2026, 11, 1)},
        )
        inputs = replace(
            inputs,
            context=replace(
                inputs.context,
                validity=(expired, *inputs.context.validity[1:]),
            ),
        )
    elif mutation == "unqualified":
        data = inputs.context.ledger.model_dump(mode="json")
        data["qualifications"][0].update(
            {
                "qualification": "unresolved",
                "blockers": ["Scope unknown"],
            },
        )
        inputs = replace(
            inputs,
            context=replace(
                inputs.context,
                ledger=QualificationLedger.model_validate(data),
            ),
        )
    else:
        data = inputs.context.ledger.model_dump(mode="json")
        data["parameter_set"][
            "version_id" if mutation == "version" else "workbook_sha256"
        ] = "other" if mutation == "version" else "d" * 64
        inputs = replace(
            inputs,
            context=replace(
                inputs.context,
                ledger=QualificationLedger.model_validate(data),
            ),
        )
    with pytest.raises(
        ValueError,
        match=r"[Ss]ource|baseline|version|evidence is unresolved",
    ):
        calculate_allocated_workflow_cost(inputs)


def test_zero_rate_and_zero_quantity_remain_explicit(tmp_path: Path) -> None:
    """Explicit qualified zeros do not establish free resources."""
    inputs = allocation_inputs(tmp_path, numerator="0", rate="0")
    result = calculate_allocated_workflow_cost(inputs)
    require_equal(result.selected_allocation_cost, Fraction(0))
    require_equal(len(result.lines), 2)
    require_equal(
        result.total_selected_cost,
        result.base_cost.total_selected_cost,
    )


def test_changed_quantity_changes_only_new_cost_and_identity(
    tmp_path: Path,
) -> None:
    """Extra quantity identity preserves legacy resource/stock hashes."""
    one = allocation_inputs(tmp_path / "one")
    two = allocation_inputs(tmp_path / "two", numerator="2")
    a = calculate_allocated_workflow_cost(one)
    b = calculate_allocated_workflow_cost(two)
    require_equal(a.base_cost.input_sha256, b.base_cost.input_sha256)
    require_equal(b.selected_allocation_cost, 2 * a.selected_allocation_cost)
    if a.input_sha256 == b.input_sha256:
        msg = "Allocation input change omitted from identity"
        raise AssertionError(msg)


def test_partial_service_keeps_requested_allocations(tmp_path: Path) -> None:
    """Requested accounting costs are distinct from completed physical work."""
    inputs = allocation_inputs(tmp_path)
    source = json.loads(inputs.workflow.inventory.stock_payload)
    for pack in source["packs"]:
        pack["arrived_seconds"] = "20"
    workflow = replace(
        inputs.workflow,
        inventory=restock(inputs.workflow.inventory, source),
    )
    result = calculate_allocated_workflow_cost(
        replace(inputs, workflow=workflow),
    )
    require_equal(result.selected_allocation_cost, Fraction(14, 3))
    require_equal(result.eligible_under_base_service_rules, expected=False)
    require_equal(result.unit_cost_per_requested_test, None)
    require_equal(
        result.reportable_cost.service_scope,
        "partial_modeled_workload",
    )


def test_no_demand_preserves_fixed_cost_and_undefined_ratios(
    tmp_path: Path,
) -> None:
    """No demand keeps existing fixed costs and undefined ratios."""
    inputs = allocation_inputs(tmp_path)
    original = inputs.workflow.inventory.workflow
    workload = original.workload.model_copy(
        update={"cases": ()},
    )
    original = replace(
        original,
        scenario=original.scenario.model_copy(
            update={"operations": ()},
        ),
    )
    inventory = replace(
        inputs.workflow.inventory,
        workflow=replace(
            original,
            workload=workload,
        ),
    )
    data = inputs.pricing.model_dump(mode="json")
    data["workload_sha256"] = allocation_workload_sha256(workload)
    data["resources"][0]["case_ids"] = []
    data["quantities"] = []
    result = calculate_allocated_workflow_cost(
        replace(
            inputs,
            workflow=replace(inputs.workflow, inventory=inventory),
            pricing=RequestedAllocationPricing.model_validate(data),
        ),
    )
    require_equal(result.selected_allocation_cost, Fraction(0))
    require_equal(result.base_cost.fixed_cost, Fraction(5))
    require_equal(result.total_selected_cost, Fraction(5))
    require_equal(result.unit_cost_per_requested_test, None)
    require_equal(result.eligible_under_base_service_rules, expected=False)


def test_declared_shared_reportable_result_is_not_case_count(
    tmp_path: Path,
) -> None:
    """Result ratios use declared unique result IDs, independently of cases."""
    inputs = allocation_inputs(tmp_path)
    original = inputs.workflow.inventory.workflow
    workload = original.workload.model_copy(
        update={
            "cases": tuple(
                c.model_copy(update={"reportable_result_ids": ("r",)})
                for c in original.workload.cases
            ),
        },
    )
    inventory = replace(
        inputs.workflow.inventory,
        workflow=replace(
            original,
            workload=workload,
        ),
    )
    pricing = inputs.pricing.model_copy(
        update={
            "workload_sha256": allocation_workload_sha256(workload),
        },
    )
    result = calculate_allocated_workflow_cost(
        replace(
            inputs,
            workflow=replace(inputs.workflow, inventory=inventory),
            pricing=pricing,
        ),
    )
    require_equal(result.reportable_cost.declared_result_count, 1)
    require_equal(
        result.reportable_cost.unit_cost_per_declared_reportable_result,
        Fraction(113, 3),
    )
    require_equal(result.unit_cost_per_requested_test, Fraction(113, 6))
