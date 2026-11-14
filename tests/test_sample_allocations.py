# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Sample allocations preserve use identity and existing costing boundaries."""

from dataclasses import replace
from fractions import Fraction
lazy from pathlib import Path

import pytest

from genomics_microcosting.sample_allocations import (
    SampleAllocationPricing,
    SampleWorkflowInputs,
    calculate_sample_allocated_workflow_cost,
)
from genomics_microcosting.workflow_allocations import (
    allocation_workload_sha256,
)
from tests.checks import require_equal
from tests.test_workflow_allocations import allocation_inputs


def sample_inputs(
    tmp_path: Path,
    *,
    numerator: str = "1",
    denominator: str = "3",
) -> SampleWorkflowInputs:
    """Use two explicit specimen relationships and source sample ratios."""
    old = allocation_inputs(
        tmp_path,
        numerator=numerator,
        denominator=denominator,
    )
    inv = old.workflow.inventory
    workload = inv.workflow.workload
    cases = tuple(
        c.model_copy(update={"specimen_ids": ("specimen",)}) for c in workload.cases
    )
    workload = workload.model_copy(update={"cases": cases})
    workflow = replace(
        old.workflow,
        inventory=replace(
            inv,
            workflow=replace(inv.workflow, workload=workload),
        ),
    )
    ledger = old.context.ledger
    params = tuple(
        p.model_copy(update={"unit": "source_sample"}) if p.parameter_id == "den" else p
        for p in ledger.parameter_set.parameters
    )
    quals = tuple(
        q.model_copy(
            update={
                "parameter": next(
                    p for p in params if p.parameter_id == q.parameter.parameter_id
                ),
                "dimensional_basis": "source_sample",
            },
        )
        if q.parameter.parameter_id == "den"
        else q
        for q in ledger.qualifications
    )
    context = replace(
        old.context,
        ledger=ledger.model_copy(
            update={
                "parameter_set": ledger.parameter_set.model_copy(
                    update={"parameters": params},
                ),
                "qualifications": quals,
            },
        ),
    )
    pricing = SampleAllocationPricing.model_validate(
        {
            "format_version": "sample-allocation-import-v1",
            "workload_sha256": allocation_workload_sha256(workload),
            "currency": "AUD",
            "price_year": 2026,
            "tax_basis": "exclusive",
            "derivation_date": "2026-11-07",
            "resources": [
                {
                    "resource_id": "extra",
                    "resource_unit": "reaction",
                    "numerator_parameter_id": "num",
                    "sample_denominator_parameter_id": "den",
                    "rate_parameter_id": "rate",
                    "case_ids": ["c1", "c2"],
                    "component_ids": ["separate-resource-allocation"],
                },
            ],
            "sample_uses": [{"use_id": "u", "specimen_id": "specimen"}],
            "shares": [
                {"use_id": "u", "case_id": c, "numerator": 1, "denominator": 2}
                for c in ("c1", "c2")
            ],
            "assumption_basis": "One proposed shared sample use; no inference",
            "scope_limit": "Only synthetic selected resource",
        },
    )
    return SampleWorkflowInputs(workflow, pricing, context)


def test_shared_use_exact_cost_and_unchanged_base(tmp_path: Path) -> None:
    """One sample split across two requests is consumed once in accounting."""
    inputs = sample_inputs(tmp_path)
    result = calculate_sample_allocated_workflow_cost(inputs)
    require_equal(result.selected_allocation_cost, Fraction(7, 3))
    require_equal(result.lines[0].quantity, Fraction(1, 6))
    require_equal(result.base_cost.total_selected_cost, Fraction(33))
    require_equal(result.total_selected_cost, Fraction(106, 3))
    require_equal(result.full_workload_cost, None)
    require_equal(calculate_sample_allocated_workflow_cost(inputs), result)


@pytest.mark.parametrize("unknown", [True, False])
def test_unknown_or_missing_attribution_rejects(
    tmp_path: Path,
    *,
    unknown: bool,
) -> None:
    """Unknown specimen relationships and incomplete use shares reject."""
    inputs = sample_inputs(tmp_path)
    if unknown:
        inv = inputs.workflow.inventory
        workload = inv.workflow.workload
        cases = (
            workload.cases[0].model_copy(
                update={"specimen_ids": None},
            ),
            *workload.cases[1:],
        )
        workload = workload.model_copy(update={"cases": cases})
        inputs = replace(
            inputs,
            workflow=replace(
                inputs.workflow,
                inventory=replace(
                    inv,
                    workflow=replace(inv.workflow, workload=workload),
                ),
            ),
            pricing=inputs.pricing.model_copy(
                update={
                    "workload_sha256": allocation_workload_sha256(workload),
                },
            ),
        )
    else:
        inputs = replace(
            inputs,
            pricing=inputs.pricing.model_copy(
                update={"shares": inputs.pricing.shares[:1]},
            ),
        )
    with pytest.raises(ValueError, match=r"Unknown specimen|conserve"):
        calculate_sample_allocated_workflow_cost(inputs)


def test_independent_uses_are_not_specimen_deduplicated(tmp_path: Path) -> None:
    """Two processing uses of one specimen remain two allocations."""
    inputs = sample_inputs(tmp_path)
    data = inputs.pricing.model_dump(mode="json")
    data["sample_uses"] = [
        {"use_id": u, "specimen_id": "specimen"} for u in ("u1", "u2")
    ]
    data["shares"] = [
        {"use_id": u, "case_id": c, "numerator": 1, "denominator": 1}
        for u, c in (("u1", "c1"), ("u2", "c2"))
    ]
    inputs = replace(
        inputs,
        pricing=SampleAllocationPricing.model_validate(data),
    )
    result = calculate_sample_allocated_workflow_cost(inputs)
    require_equal(result.selected_allocation_cost, Fraction(14, 3))
    require_equal(result.lines[0].quantity, Fraction(1, 3))
    data["sample_uses"][0]["use_id"] = "different-use"
    data["shares"][0]["use_id"] = "different-use"
    successor = replace(
        inputs,
        pricing=SampleAllocationPricing.model_validate(data),
    )
    other = calculate_sample_allocated_workflow_cost(successor)
    require_equal(
        other.selected_allocation_cost,
        result.selected_allocation_cost,
    )
    require_equal(other.input_sha256 == result.input_sha256, expected=False)


@pytest.mark.parametrize(
    ("key", "value", "error"),
    [
        ("currency", "USD", "economic frame"),
        ("price_year", 2023, "economic frame"),
        ("tax_basis", "inclusive", "economic frame"),
        ("tax_basis", "unknown", "inclusive.*exclusive"),
        ("workload_sha256", "f" * 64, "workload identity"),
    ],
)
def test_source_frame_and_workload_guards(
    tmp_path: Path,
    key: str,
    value: object,
    error: str,
) -> None:
    """A new normalizer retains existing source/frame and workload guards."""
    inputs = sample_inputs(tmp_path)
    inputs = replace(
        inputs,
        pricing=inputs.pricing.model_copy(
            update={key: value},
        ),
    )
    with pytest.raises(ValueError, match=error):
        calculate_sample_allocated_workflow_cost(inputs)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("use_id", "foreign", "unknown use"),
        ("case_id", "foreign", "selected case"),
        ("numerator", 2, "conserve"),
        ("numerator", -1, "greater than"),
        ("numerator", True, "valid integer"),
        ("denominator", 0, "greater than"),
    ],
)
def test_invalid_shares_reject(
    tmp_path: Path,
    field: str,
    value: object,
    error: str,
) -> None:
    """Invalid shares cannot hide unknown, excessive or negative use."""
    inputs = sample_inputs(tmp_path)
    shares = (
        inputs.pricing.shares[0].model_copy(update={field: value}),
        *inputs.pricing.shares[1:],
    )
    inputs = replace(
        inputs,
        pricing=inputs.pricing.model_copy(
            update={"shares": shares},
        ),
    )
    with pytest.raises(ValueError, match=error):
        calculate_sample_allocated_workflow_cost(inputs)


@pytest.mark.parametrize("kind", ["use", "share", "specimen", "coverage"])
def test_duplicate_and_foreign_mapping_rejects(
    tmp_path: Path,
    kind: str,
) -> None:
    """Full attribution is explicit, unique and tied to declared specimens."""
    inputs = sample_inputs(tmp_path)
    data = inputs.pricing.model_dump(mode="json")
    if kind == "use":
        data["sample_uses"] *= 2
    elif kind == "share":
        data["shares"].append(data["shares"][0])
    elif kind == "specimen":
        data["sample_uses"][0]["specimen_id"] = "foreign"
    else:
        data["shares"] = [data["shares"][0] | {"denominator": 1}]
    inputs = replace(
        inputs,
        pricing=SampleAllocationPricing.model_validate(data),
    )
    with pytest.raises(ValueError, match=r"Duplicate|outside|incomplete"):
        calculate_sample_allocated_workflow_cost(inputs)


@pytest.mark.parametrize("denominator", ["0", "1.5"])
def test_sample_denominator_is_positive_whole(
    tmp_path: Path,
    denominator: str,
) -> None:
    """Source sample counts are neither zero nor fractional counts."""
    inputs = sample_inputs(tmp_path, denominator=denominator)
    with pytest.raises(ValueError, match="whole samples"):
        calculate_sample_allocated_workflow_cost(inputs)


def test_source_tampering_and_negative_quantity_reject(tmp_path: Path) -> None:
    """Original snapshots remain live-verified before any derived parameter."""
    inputs = sample_inputs(tmp_path / "negative", numerator="-1")
    with pytest.raises(ValueError, match="nonnegative numeric"):
        calculate_sample_allocated_workflow_cost(inputs)
    inputs = sample_inputs(tmp_path / "tampered")
    inputs.context.snapshots["num"].write_text("999\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        calculate_sample_allocated_workflow_cost(inputs)


def test_component_overlap_still_rejects(tmp_path: Path) -> None:
    """Derivative normalization does not relax economic nonoverlap."""
    inputs = sample_inputs(tmp_path)
    resource = inputs.pricing.resources[0].model_copy(
        update={
            "component_ids": ("staff-time",),
        },
    )
    inputs = replace(
        inputs,
        pricing=inputs.pricing.model_copy(
            update={
                "resources": (resource,),
            },
        ),
    )
    with pytest.raises(ValueError, match="overlap"):
        calculate_sample_allocated_workflow_cost(inputs)


def test_explicit_zero_and_empty_selection_preserve_scope(
    tmp_path: Path,
) -> None:
    """Reported zero and intentionally unselected resources are explicit."""
    inputs = sample_inputs(tmp_path, numerator="0")
    result = calculate_sample_allocated_workflow_cost(inputs)
    require_equal(result.selected_allocation_cost, Fraction(0))
    require_equal(
        result.total_selected_cost,
        result.base_cost.total_selected_cost,
    )
    inputs = replace(
        inputs,
        pricing=inputs.pricing.model_copy(
            update={
                "resources": (),
                "sample_uses": (),
                "shares": (),
            },
        ),
    )
    other = calculate_sample_allocated_workflow_cost(inputs)
    require_equal(other.selected_allocation_cost, Fraction(0))
    require_equal(other.lines, ())
    require_equal(other.full_workload_cost, None)


@pytest.mark.parametrize("field", ["case_ids", "component_ids"])
def test_duplicate_resource_scope_rejects(tmp_path: Path, field: str) -> None:
    """Existing selection coverage and component uniqueness remain strict."""
    inputs = sample_inputs(tmp_path)
    resource = inputs.pricing.resources[0]
    values = getattr(resource, field)
    resource = resource.model_copy(update={field: (*values, values[0])})
    inputs = replace(
        inputs,
        pricing=inputs.pricing.model_copy(
            update={
                "resources": (resource,),
            },
        ),
    )
    with pytest.raises(ValueError, match="Duplicate"):
        calculate_sample_allocated_workflow_cost(inputs)


def test_unbounded_source_quantity_rejects(tmp_path: Path) -> None:
    """The adapter retains the existing 128-digit numeric profile."""
    inputs = sample_inputs(tmp_path, numerator="1e129")
    with pytest.raises(ValueError, match="numeric profile"):
        calculate_sample_allocated_workflow_cost(inputs)


def test_derivation_date_is_separate_and_hash_bound(tmp_path: Path) -> None:
    """Computed snapshot dates do not pretend to be historical retrievals."""
    inputs = sample_inputs(tmp_path)
    first = calculate_sample_allocated_workflow_cost(inputs)
    data = inputs.pricing.model_dump(mode="json")
    data["derivation_date"] = "2026-11-08"
    second = calculate_sample_allocated_workflow_cost(
        replace(
            inputs,
            pricing=SampleAllocationPricing.model_validate(data),
        ),
    )
    require_equal(
        first.selected_allocation_cost,
        second.selected_allocation_cost,
    )
    require_equal(first.input_sha256 == second.input_sha256, expected=False)
    data["derivation_date"] = "2026-11-06"
    with pytest.raises(ValueError, match="predates retained source"):
        calculate_sample_allocated_workflow_cost(
            replace(
                inputs,
                pricing=SampleAllocationPricing.model_validate(data),
            ),
        )
