# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Exercise unqualified resource accounting and conservation failures."""

from decimal import Decimal, Inexact

import pytest

from genomics_microcosting.provenance_ledger import Parameter, ParameterSet
from genomics_microcosting.resource_accounting import (
    BaselineDisposition,
    DraftParameterBindings,
    DraftResourceComparison,
    ResourceLine,
    ResourceParameterBinding,
)
from tests import checks


def line(name: str, quantity: str, cost: str) -> ResourceLine:
    """Create a synthetic item-based resource."""
    return ResourceLine(
        resource_id=name,
        quantity=Decimal(quantity),
        quantity_unit="item",
        unit_cost=Decimal(cost),
        cost_denominator_unit="item",
        currency="AUD",
        allocation=Decimal(1),
    )


def test_draft_replays_baseline_and_counts_stranded_and_new_resources() -> None:
    """An alternative includes retained, replaced, stranded and added lines once."""
    retained, replaced, stranded = (
        line("labour", "2", "3"),
        line("kit", "1", "9"),
        line("capital", "1", "5"),
    )
    alternative, abandoned, added = (
        line("new-kit", "1", "7"),
        line("idle-capital", "1", "5"),
        line("qc", "1", "2"),
    )
    old_kit_residual = line("old-kit-residual", "1", "2")
    draft = DraftResourceComparison(
        baseline=(retained, replaced, stranded),
        candidate=(retained, alternative, abandoned, added, old_kit_residual),
        dispositions=(
            BaselineDisposition(
                baseline_resource_id="labour",
                action="retained",
                candidate_resource_ids=("labour",),
                residual_treatment="none",
                stranded_resource_ids=(),
            ),
            BaselineDisposition(
                baseline_resource_id="kit",
                action="replaced",
                candidate_resource_ids=("new-kit",),
                residual_treatment="stranded",
                stranded_resource_ids=("old-kit-residual",),
            ),
            BaselineDisposition(
                baseline_resource_id="capital",
                action="stranded",
                candidate_resource_ids=(),
                residual_treatment="stranded",
                stranded_resource_ids=("idle-capital",),
            ),
        ),
        added_candidate_ids=("qc",),
        baseline_total=Decimal(20),
        functional_unit="sample",
        currency="AUD",
    )
    checks.require_equal(draft.calculate_draft(), (Decimal(22), Decimal(2)))
    invalid = draft.model_copy(update={"baseline_total": Decimal(19)})
    with pytest.raises(ValueError, match="replay"):
        invalid.calculate_draft()
    duplicate = draft.model_copy(update={"added_candidate_ids": ("qc", "new-kit")})
    with pytest.raises(ValueError, match="counted more than once"):
        duplicate.calculate_draft()
    missing = draft.model_copy(update={"dispositions": draft.dispositions[:-1]})
    with pytest.raises(ValueError, match="disposition coverage"):
        missing.calculate_draft()
    changed = draft.model_copy(
        update={
            "candidate": (
                line("labour", "2", "4"),
                alternative,
                abandoned,
                added,
                old_kit_residual,
            ),
        },
    )
    with pytest.raises(ValueError, match="preserve its baseline line"):
        changed.calculate_draft()
    with pytest.raises(ValueError, match="Duplicate candidate resource mapping"):
        BaselineDisposition(
            baseline_resource_id="kit",
            action="replaced",
            candidate_resource_ids=("new-kit",),
            residual_treatment="stranded",
            stranded_resource_ids=("new-kit",),
        )
    with pytest.raises(ValueError, match="stranded resource mapping"):
        BaselineDisposition(
            baseline_resource_id="kit",
            action="replaced",
            candidate_resource_ids=("new-kit",),
            residual_treatment="stranded",
            stranded_resource_ids=(),
        )


def test_resource_values_reject_missing_units_and_nonfinite_amounts() -> None:
    """Costs and allocation must be explicit, finite, and dimensionally aligned."""
    good = line("kit", "1", "2")
    for change in (
        {"quantity": None},
        {"unit_cost": Decimal("NaN")},
        {"allocation": Decimal("1.01")},
        {"cost_denominator_unit": "box"},
    ):
        with pytest.raises(
            ValueError,
            match=r"quantity|unit_cost|allocation|units differ",
        ):
            ResourceLine.model_validate(good.model_dump() | change)


def test_resource_arithmetic_rejects_silent_precision_loss() -> None:
    """Large input precision must not silently round an allocated cost."""
    value = line(
        "precise",
        "1.123456789012345678901234567890",
        "1.123456789012345678901234567890",
    )
    with pytest.raises(Inexact):
        value.cost()


def test_draft_bindings_require_exact_parameters_units_and_coverage() -> None:
    """Every draft line and total must match an explicit parameter version."""

    def param(name: str, value: str, unit: str) -> Parameter:
        return Parameter(
            parameter_id=name,
            raw_value=value,
            derived_value=value,
            unit=unit,
            source_sha256="a" * 64,
            source_locator="A1",
            transformation="identity",
            uncertainty="unknown",
            status="observed",
        )

    resource = line("kit", "2", "3")
    draft = DraftResourceComparison(
        baseline=(resource,),
        candidate=(resource,),
        dispositions=(
            BaselineDisposition(
                baseline_resource_id="kit",
                action="retained",
                candidate_resource_ids=("kit",),
                residual_treatment="none",
                stranded_resource_ids=(),
            ),
        ),
        added_candidate_ids=(),
        baseline_total=Decimal(6),
        functional_unit="sample",
        currency="AUD",
    )
    parameters = ParameterSet(
        version_id="v1",
        workbook_sha256="a" * 64,
        parameters=(
            param("quantity", "2", "item/sample"),
            param("price", "3", "AUD/item"),
            param("allocation", "1", "fraction"),
            param("baseline", "6", "AUD/sample"),
        ),
    )
    binding = ResourceParameterBinding(
        arm="baseline",
        resource_id="kit",
        quantity_parameter_id="quantity",
        unit_cost_parameter_id="price",
        allocation_parameter_id="allocation",
    )
    bindings = DraftParameterBindings(
        parameter_version_id="v1",
        baseline_total_parameter_id="baseline",
        lines=(binding, binding.model_copy(update={"arm": "candidate"})),
    )
    bindings.verify_values(draft, parameters)
    wrong_basis = parameters.model_copy(
        update={
            "parameters": (
                param("quantity", "2", "item"),
                *parameters.parameters[1:],
            ),
        },
    )
    with pytest.raises(ValueError, match="value or unit"):
        bindings.verify_values(draft, wrong_basis)
    with pytest.raises(ValueError, match="coverage"):
        bindings.model_copy(update={"lines": (binding,)}).verify_values(
            draft,
            parameters,
        )
    wrong = parameters.model_copy(
        update={
            "parameters": (
                *parameters.parameters[:-1],
                param("baseline", "7", "AUD/sample"),
            ),
        },
    )
    with pytest.raises(ValueError, match="value or unit"):
        bindings.verify_values(draft, wrong)
    wrong_unit = parameters.model_copy(
        update={
            "parameters": (
                parameters.parameters[0],
                param("price", "3", "AUD/box"),
                *parameters.parameters[2:],
            ),
        },
    )
    with pytest.raises(ValueError, match="value or unit"):
        bindings.verify_values(draft, wrong_unit)
    unresolved = parameters.parameters[0].model_copy(
        update={"status": "unresolved", "derived_value": None},
    )
    with pytest.raises(ValueError, match="missing or unresolved"):
        bindings.verify_values(
            draft,
            parameters.model_copy(
                update={"parameters": (unresolved, *parameters.parameters[1:])},
            ),
        )
