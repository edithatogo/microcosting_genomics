# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Price declared resource components without inventing event schedules."""

from dataclasses import replace
from fractions import Fraction
lazy from pathlib import Path

import pytest

from genomics_microcosting import workflow_allocations
from genomics_microcosting.component_allocations import (
    AllocationCohort,
    ComponentAllocationInputs,
    ComponentAllocationPricing,
    component_cohort_sha256,
    price_component_allocations,
)
from tests import checks
from tests.test_workflow_allocations import allocation_inputs


def component_inputs(
    tmp_path: Path,
    *,
    numerator: str = "1",
    denominator: str = "3",
    rate: str = "7",
    units: tuple[str, str] = ("reaction", "reaction"),
) -> ComponentAllocationInputs:
    """Reuse numeric evidence only; event/workflow inputs are not passed."""
    old = allocation_inputs(
        tmp_path,
        numerator=numerator,
        denominator=denominator,
        rate=rate,
        units=units,
    )
    cases = tuple(
        c.model_copy(update={"arrival_seconds": None})
        for c in old.workflow.inventory.workflow.workload.cases
    )
    cohort = AllocationCohort(
        format_version="allocation-cohort-v1",
        cohort_id="standalone",
        process_id="source-allocation",
        baseline_sha256=old.context.ledger.parameter_set.workbook_sha256,
        parameter_version_id=old.context.ledger.parameter_set.version_id,
        source_workload_sha256=None,
        cases=cases,
        evidence_state="assumed",
        assumption_basis="Declared accounting cohort; timing unknown",
    )
    p = old.pricing.model_dump(mode="json")
    p.pop("format_version")
    p.pop("workload_sha256")
    p.pop("allocation_basis")
    pricing = ComponentAllocationPricing(
        format_version="component-allocation-cost-v1",
        cohort_sha256=component_cohort_sha256(cohort),
        **p,
    )
    return ComponentAllocationInputs(cohort, pricing, old.context)


def test_exact_components_do_not_require_scheduled_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Price components without inferring clocks, stock or completed service."""

    def forbidden(_: object) -> None:
        pytest.fail("A standalone component quote called the workflow engine")

    inputs = component_inputs(tmp_path)
    monkeypatch.setattr(
        workflow_allocations,
        "calculate_workflow_cost",
        forbidden,
    )
    result = price_component_allocations(inputs)
    checks.require_equal(result.selected_component_cost, Fraction(14, 3))
    checks.require_equal(
        result.component_cost_per_declared_requested_test,
        Fraction(7, 3),
    )
    checks.require_equal(result.service_coverage, "not_assessed")
    checks.require_equal(result.physical_feasibility, "not_assessed")
    checks.require_equal(result.full_workload_cost, None)
    checks.require_equal(result.cost_per_reportable_result, None)
    checks.require_equal(len(result.lines), 2)
    checks.require_equal(
        sum((cost for _, cost in result.case_component_costs), Fraction(0)),
        result.selected_component_cost,
    )


@pytest.mark.parametrize("field", ["baseline_sha256", "parameter_version_id"])
def test_source_cohort_frame_cannot_be_changed(
    tmp_path: Path,
    field: str,
) -> None:
    """Matching cohort bytes still require the source baseline/version frame."""
    inputs = component_inputs(tmp_path)
    value = "a" * 64 if field == "baseline_sha256" else "other-version"
    cohort = inputs.cohort.model_copy(update={field: value})
    pricing = inputs.pricing.model_copy(
        update={"cohort_sha256": component_cohort_sha256(cohort)},
    )
    with pytest.raises(ValueError, match="baseline/version"):
        price_component_allocations(
            replace(inputs, cohort=cohort, pricing=pricing),
        )


def test_cohort_hash_guards_known_and_unknown_relationships(
    tmp_path: Path,
) -> None:
    """Bind changed entity relationships to a newly selected quote."""
    inputs = component_inputs(tmp_path)
    data = inputs.cohort.model_dump(mode="json")
    data["cases"][0]["specimen_ids"] = ["sample"]
    with pytest.raises(ValueError, match="cohort identity"):
        price_component_allocations(
            replace(inputs, cohort=AllocationCohort.model_validate(data)),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [("case_id", "c1"), ("requested_test_id", "test-c1")],
)
def test_duplicate_case_or_request_is_rejected(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    """Two rows cannot silently represent the same requested test."""
    inputs = component_inputs(tmp_path)
    data = inputs.cohort.model_dump(mode="json")
    data["cases"][1][field] = value
    with pytest.raises(ValueError, match="Duplicate"):
        AllocationCohort.model_validate(data)


@pytest.mark.parametrize("denominator", ["0", "-1", "1.5"])
def test_allocation_denominator_is_positive_whole_requests(
    tmp_path: Path,
    denominator: str,
) -> None:
    """No missing, zero or fractional requested cohort is inferred."""
    inputs = component_inputs(tmp_path, denominator=denominator)
    with pytest.raises(ValueError, match=r"positive whole|nonnegative"):
        price_component_allocations(inputs)


def test_currency_and_resource_units_are_checked(tmp_path: Path) -> None:
    """An AUD resource price is not a currency or resource conversion."""
    inputs = component_inputs(tmp_path)
    with pytest.raises(ValueError, match="unit mismatch"):
        price_component_allocations(
            replace(
                inputs,
                pricing=inputs.pricing.model_copy(update={"currency": "USD"}),
            ),
        )


def test_source_tampering_is_reverified(tmp_path: Path) -> None:
    """A prior quote does not authorize changed source bytes."""
    inputs = component_inputs(tmp_path)
    price_component_allocations(inputs)
    inputs.context.snapshots["num"].write_text("9\n")
    with pytest.raises(ValueError, match="hash"):
        price_component_allocations(inputs)


def test_unknown_case_and_missing_pairs_reject(tmp_path: Path) -> None:
    """Complete selected resource/case coverage is separate from service."""
    inputs = component_inputs(tmp_path)
    data = inputs.pricing.model_dump(mode="json")
    data["resources"][0]["case_ids"] = ["missing"]
    data["quantities"] = [data["quantities"][0]]
    data["quantities"][0]["case_id"] = "missing"
    pricing = ComponentAllocationPricing.model_validate(data)
    with pytest.raises(ValueError, match="unknown requested case"):
        price_component_allocations(replace(inputs, pricing=pricing))
    data = inputs.pricing.model_dump(mode="json")
    data["quantities"] = data["quantities"][:1]
    with pytest.raises(ValueError, match="cover"):
        ComponentAllocationPricing.model_validate(data)


def test_duplicate_components_reject_even_with_distinct_resource_ids(
    tmp_path: Path,
) -> None:
    """Unique identifiers cannot disguise a repeated economic component."""
    inputs = component_inputs(tmp_path)
    data = inputs.pricing.model_dump(mode="json")
    other = {**data["resources"][0], "resource_id": "other"}
    data["resources"].append(other)
    with pytest.raises(ValueError, match="Duplicate"):
        ComponentAllocationPricing.model_validate(data)


def test_empty_selection_preserves_zero_scope_and_unknown_full_cost(
    tmp_path: Path,
) -> None:
    """No selected quantity is not proof of free full-service work."""
    inputs = component_inputs(tmp_path)
    cohort = inputs.cohort.model_copy(update={"cases": ()})
    pricing = inputs.pricing.model_copy(
        update={
            "cohort_sha256": component_cohort_sha256(cohort),
            "resources": (),
            "quantities": (),
        },
    )
    result = price_component_allocations(
        replace(inputs, cohort=cohort, pricing=pricing),
    )
    checks.require_equal(result.selected_component_cost, Fraction(0))
    checks.require_equal(
        result.component_cost_per_declared_requested_test,
        None,
    )
    checks.require_equal(result.full_workload_cost, None)
    checks.require_equal(result.service_coverage, "not_assessed")


def test_zero_quantity_is_explicit_and_does_not_create_reported_results(
    tmp_path: Path,
) -> None:
    """An evidenced zero selected quantity does not establish service/yield."""
    inputs = component_inputs(tmp_path, numerator="0")
    result = price_component_allocations(inputs)
    checks.require_equal(result.selected_component_cost, Fraction(0))
    checks.require_equal(result.cost_per_reportable_result, None)
    checks.require_equal(result.full_workload_cost, None)


def test_source_choice_changes_input_identity(tmp_path: Path) -> None:
    """Scope and frame declarations remain part of the selected quote."""
    inputs = component_inputs(tmp_path)
    first = price_component_allocations(inputs)
    changed = price_component_allocations(
        replace(
            inputs,
            pricing=inputs.pricing.model_copy(update={"scope_limit": "other"}),
        ),
    )
    checks.require_equal(
        first.input_sha256 != changed.input_sha256,
        expected=True,
    )
    checks.require_equal(
        first.selected_component_cost,
        changed.selected_component_cost,
    )


def test_declared_unused_rate_still_requires_matching_units(
    tmp_path: Path,
) -> None:
    """An empty resource selection does not excuse a malformed declared rate."""
    inputs = component_inputs(tmp_path)
    data = inputs.pricing.model_dump(mode="json")
    data["currency"] = "USD"
    data["resources"][0]["case_ids"] = []
    data["quantities"] = []
    pricing = ComponentAllocationPricing.model_validate(data)
    with pytest.raises(ValueError, match="unit mismatch"):
        price_component_allocations(replace(inputs, pricing=pricing))


def test_entity_counts_do_not_rewrite_declared_resource_quantities(
    tmp_path: Path,
) -> None:
    """Specimen identities are retained without an automatic trio multiplier."""
    inputs = component_inputs(tmp_path, numerator="3", denominator="1")
    first = price_component_allocations(inputs)
    data = inputs.cohort.model_dump(mode="json")
    data["cases"][0]["specimen_ids"] = ["s1", "s2", "s3"]
    cohort = AllocationCohort.model_validate(data)
    pricing = inputs.pricing.model_copy(
        update={"cohort_sha256": component_cohort_sha256(cohort)},
    )
    changed = price_component_allocations(
        replace(inputs, cohort=cohort, pricing=pricing),
    )
    checks.require_equal(changed.selected_component_cost, Fraction(42))
    checks.require_equal(
        first.selected_component_cost,
        changed.selected_component_cost,
    )
    checks.require_equal(
        first.input_sha256 != changed.input_sha256,
        expected=True,
    )
