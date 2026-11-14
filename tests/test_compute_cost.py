# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify source-bound compute arithmetic and basis separation."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    ComputeMeter,
    ComputePricing,
    calculate_compute_cost,
)
from genomics_microcosting.provenance_ledger import (
    Parameter,
    ParameterQualification,
    ParameterSet,
    QualificationLedger,
    SourceRecord,
    SourceValidity,
)
from tests import checks


def inputs(
    tmp_path: Path,
    quantity: str = "10",
    bill: str = "25",
) -> tuple[ComputePricing, ComputeCostContext]:
    """Build synthetic retained numeric sources, with no real rate claim."""
    parameters: list[Parameter] = []
    qualified: list[ParameterQualification] = []
    validity: list[SourceValidity] = []
    snapshots: dict[str, Path] = {}
    for name, value, unit in (
        ("quantity", quantity, "core_s"),
        ("rate", "2", "AUD/core_s"),
        ("share", "0.5", "fraction"),
        ("bill", bill, "AUD"),
    ):
        path = tmp_path / f"{name}.txt"
        path.write_text(value + "\n", encoding="utf-8")
        digest = sha256(path.read_bytes()).hexdigest()
        p = Parameter(
            parameter_id=name,
            raw_value=value,
            derived_value=value,
            unit=unit,
            source_sha256=digest,
            source_locator="line 1",
            transformation="identity",
            uncertainty="synthetic",
            status="reported",
        )
        source = SourceRecord(
            source_id=name,
            sha256=digest,
            edition="synthetic",
            locator="line 1",
            limitations="synthetic only",
        )
        parameters.append(p)
        qualified.append(
            ParameterQualification(
                parameter=p,
                source=source,
                exact_support=value,
                dimensional_basis=unit,
                applicability="synthetic",
                qualification="qualified",
                blockers=(),
            ),
        )
        validity.append(
            SourceValidity(
                source=source,
                retrieved=date(2026, 11, 6),
                effective_from=date(2026, 1, 1),
                effective_until=date(2026, 12, 31),
                date_basis="synthetic",
            ),
        )
        snapshots[name] = path
    ledger = QualificationLedger(
        parameter_set=ParameterSet(
            version_id="v1",
            workbook_sha256="f" * 64,
            parameters=tuple(parameters),
        ),
        qualifications=tuple(qualified),
    )
    context = ComputeCostContext(
        ledger=ledger,
        snapshots=snapshots,
        validity=tuple(validity),
        costing_date=date(2026, 6, 1),
    )
    meter = ComputeMeter(
        meter_id="cpu",
        quantity_parameter_id="quantity",
        rate_parameter_id="rate",
        allocation_parameter_id="share",
        unit="core_s",
        usage_basis="measured",
        price_basis="measured",
    )
    pricing = ComputePricing(
        function_version="compute-cost-v1",
        workload_id="w",
        price_year=2026,
        currency="AUD",
        tax_basis="inclusive",
        meters=(meter,),
        bill_parameter_id="bill",
    )
    return pricing, context


def test_compute_cost_reconciles_total_allocation_and_bill_residual(
    tmp_path: Path,
) -> None:
    """Quantity times rate, allocation and independent bill reconcile exactly."""
    pricing, context = inputs(tmp_path)
    result = calculate_compute_cost(pricing, context)
    checks.require_equal(
        (
            result.modeled_total,
            result.allocated_cost,
            result.unallocated_cost,
            result.bill_residual,
        ),
        (Decimal(20), Decimal(10), Decimal(10), Decimal(5)),
    )
    context.snapshots["rate"].write_text("3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        calculate_compute_cost(pricing, context)


def test_compute_cost_rejects_implicit_basis_conversion_and_invalid_date(
    tmp_path: Path,
) -> None:
    """Requested capacity cannot be priced as measured usage by inference."""
    pricing, context = inputs(tmp_path)
    wrong = pricing.meters[0].model_copy(update={"price_basis": "requested"})
    with pytest.raises(ValueError, match="basis"):
        calculate_compute_cost(pricing.model_copy(update={"meters": (wrong,)}), context)
    with pytest.raises(ValueError, match="does not cover"):
        calculate_compute_cost(pricing, replace(context, costing_date=date(2027, 1, 1)))


@pytest.mark.parametrize(
    ("quantity", "bill", "total", "residual"),
    [
        ("0", "25", Decimal(0), Decimal(25)),
        ("10", "15", Decimal(20), Decimal(-5)),
    ],
)
def test_zero_usage_and_signed_bill_residual_remain_explicit(
    tmp_path: Path,
    quantity: str,
    bill: str,
    total: Decimal,
    residual: Decimal,
) -> None:
    """Zero modeled use is not a claim of zero fixed cost; residuals retain sign."""
    pricing, context = inputs(tmp_path, quantity, bill)
    result = calculate_compute_cost(pricing, context)
    checks.require_equal(
        (result.modeled_total, result.bill_residual),
        (total, residual),
    )


def test_duplicate_quantity_and_wrong_meter_units_fail_closed(tmp_path: Path) -> None:
    """Renaming a meter cannot count the same quantity twice."""
    pricing, context = inputs(tmp_path)
    first = pricing.meters[0]
    duplicate = first.model_copy(update={"meter_id": "other"})
    with pytest.raises(ValueError, match="count usage twice"):
        calculate_compute_cost(
            pricing.model_copy(update={"meters": (first, duplicate)}),
            context,
        )
    wrong = first.model_copy(update={"unit": "byte_s"})
    with pytest.raises(ValueError, match="unit differs"):
        calculate_compute_cost(pricing.model_copy(update={"meters": (wrong,)}), context)


def test_absent_bill_produces_unknown_residual(tmp_path: Path) -> None:
    """No bill is not represented as a zero charge or zero residual."""
    pricing, context = inputs(tmp_path)
    selected = context.ledger.parameter_set.model_copy(
        update={"parameters": context.ledger.parameter_set.parameters[:-1]},
    )
    ledger = context.ledger.model_copy(
        update={
            "parameter_set": selected,
            "qualifications": context.ledger.qualifications[:-1],
        },
    )
    result = calculate_compute_cost(
        pricing.model_copy(update={"bill_parameter_id": None}),
        replace(context, ledger=ledger),
    )
    checks.require_equal(result.bill_residual, None)
