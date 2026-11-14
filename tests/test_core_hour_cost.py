# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Keep hourly capacity sources explicit without changing frozen seconds pricing."""

from dataclasses import replace
from decimal import Decimal, Inexact, localcontext
lazy from pathlib import Path

import pytest

from genomics_microcosting.compute_cost import (
    ComputeMeter,
    ComputePricing,
    CoreHourMeter,
    CoreHourPricing,
    calculate_compute_cost,
    calculate_core_hour_cost,
)
from tests.checks import require_equal
from tests.test_compute_cost import inputs
from tests.test_native_compute_cost import native_inputs
lazy from genomics_microcosting.compute_cost import ComputeCostContext


def hourly_inputs(
    tmp_path: Path,
    quantity: str = "10",
) -> tuple[CoreHourPricing, ComputeCostContext]:
    """Change only explicitly declared synthetic units, not numeric values."""
    seconds, context = inputs(tmp_path, quantity=quantity)
    units = {"quantity": "core_h", "rate": "AUD/core_h"}
    qualifications = tuple(
        record.model_copy(
            update={
                "parameter": record.parameter.model_copy(
                    update={
                        "unit": units.get(
                            record.parameter.parameter_id,
                            record.parameter.unit,
                        ),
                    },
                ),
                "dimensional_basis": units.get(
                    record.parameter.parameter_id,
                    record.dimensional_basis,
                ),
            },
        )
        for record in context.ledger.qualifications
    )
    ledger = context.ledger.model_copy(
        update={
            "qualifications": qualifications,
            "parameter_set": context.ledger.parameter_set.model_copy(
                update={
                    "parameters": tuple(r.parameter for r in qualifications),
                },
            ),
        },
    )
    pricing = CoreHourPricing.model_validate(
        {
            **seconds.model_dump(),
            "function_version": "compute-core-hour-cost-v1",
            "meters": [{**m.model_dump(), "unit": "core_h"} for m in seconds.meters],
        },
    )
    return pricing, replace(context, ledger=ledger)


@pytest.mark.parametrize(
    ("quantity", "total", "allocated", "residual"),
    [
        ("0", "0", "0", "25"),
        ("0.25", "0.50", "0.250", "24.50"),
        ("3", "6", "3.0", "19"),
        ("20", "40", "20.0", "-15"),
    ],
)
def test_hourly_source_cost_allocation_and_signed_residual(
    tmp_path: Path,
    quantity: str,
    total: str,
    allocated: str,
    residual: str,
) -> None:
    """Original hour units preserve exact totals, fractions, zero and overrun."""
    pricing, context = hourly_inputs(tmp_path, quantity)
    result = calculate_core_hour_cost(pricing, context)
    require_equal(result.modeled_total, Decimal(total))
    require_equal(result.allocated_cost, Decimal(allocated))
    require_equal(
        result.allocated_cost + result.unallocated_cost,
        result.modeled_total,
    )
    require_equal(result.bill_residual, Decimal(residual))


def test_hour_rate_does_not_need_inexact_seconds_conversion(tmp_path: Path) -> None:
    """Two currency units/hour is exact although its per-second rate repeats."""
    with localcontext() as context:
        context.prec = 50
        context.traps[Inexact] = True
        with pytest.raises(Inexact):
            _ = Decimal(2) / Decimal(3600)
    pricing, context = hourly_inputs(tmp_path, "3")
    require_equal(calculate_core_hour_cost(pricing, context).modeled_total, Decimal(6))


def test_frozen_seconds_contract_stays_separate(tmp_path: Path) -> None:
    """Both entry points reject the other version and never infer a conversion."""
    hours, context = hourly_inputs(tmp_path)
    with pytest.raises(ValueError, match="function_version"):
        ComputePricing.model_validate(hours.model_dump())
    with pytest.raises(ValueError, match="unit"):
        ComputeMeter.model_validate(hours.meters[0].model_dump())
    seconds = ComputePricing.model_validate(
        {
            **hours.model_dump(),
            "function_version": "compute-cost-v1",
            "meters": [{**m.model_dump(), "unit": "core_s"} for m in hours.meters],
        },
    )
    with pytest.raises(ValueError, match="unit differs"):
        calculate_compute_cost(seconds, context)
    with pytest.raises(ValueError, match="function_version"):
        CoreHourPricing.model_validate(seconds.model_dump())


def test_hourly_cost_rejects_seconds_sources_and_tampering(tmp_path: Path) -> None:
    """Matching numbers do not convert a seconds source to hour capacity."""
    pricing, context = inputs(tmp_path)
    hours = CoreHourPricing.model_validate(
        {
            **pricing.model_dump(),
            "function_version": "compute-core-hour-cost-v1",
            "meters": [{**m.model_dump(), "unit": "core_h"} for m in pricing.meters],
        },
    )
    with pytest.raises(ValueError, match="unit differs"):
        calculate_core_hour_cost(hours, context)
    context.snapshots["rate"].write_text("3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        calculate_core_hour_cost(hours, context)


def test_native_cpu_seconds_cannot_be_read_as_hours(tmp_path: Path) -> None:
    """Native source profiles still require their original core_s scalar units."""
    pricing, context = native_inputs(tmp_path)
    hours = CoreHourPricing.model_validate(
        {
            **pricing.model_dump(),
            "function_version": "compute-core-hour-cost-v1",
            "meters": [{**m.model_dump(), "unit": "core_h"} for m in pricing.meters],
        },
    )
    with pytest.raises(ValueError, match="unit differs"):
        calculate_core_hour_cost(hours, context)
    records = tuple(
        record.model_copy(
            update={
                "parameter": record.parameter.model_copy(update={"unit": "core_h"}),
            },
        )
        if record.source.locator.startswith("wait4:")
        else record
        for record in context.ledger.qualifications
    )
    relabeled = context.ledger.model_copy(
        update={
            "qualifications": records,
            "parameter_set": context.ledger.parameter_set.model_copy(
                update={
                    "parameters": tuple(r.parameter for r in records),
                },
            ),
        },
    )
    with pytest.raises(ValueError, match="source locator or unit"):
        calculate_core_hour_cost(hours, replace(context, ledger=relabeled))


def test_hourly_schema_rejects_duplicate_and_mixed_bases(tmp_path: Path) -> None:
    """A new version retains identity, basis and quantity-uniqueness guards."""
    pricing, _ = hourly_inputs(tmp_path)
    first = pricing.meters[0]
    with pytest.raises(ValueError, match="basis"):
        CoreHourMeter.model_validate(
            {
                **first.model_dump(),
                "price_basis": "allocated",
            },
        )
    with pytest.raises(ValueError, match="Duplicate compute meter"):
        CoreHourPricing.model_validate(
            {
                **pricing.model_dump(),
                "meters": [first.model_dump()] * 2,
            },
        )
    with pytest.raises(ValueError, match="count usage twice"):
        CoreHourPricing.model_validate(
            {
                **pricing.model_dump(),
                "meters": [
                    first.model_dump(),
                    {
                        **first.model_dump(),
                        "meter_id": "alias",
                    },
                ],
            },
        )


def test_hourly_missing_price_and_inexact_arithmetic_fail(tmp_path: Path) -> None:
    """Missing prices remain missing; the 50-digit precision guard stays intact."""
    pricing, context = hourly_inputs(tmp_path, "1234567890" * 6)
    with pytest.raises(Inexact):
        calculate_core_hour_cost(pricing, context)
    missing = pricing.model_copy(
        update={
            "meters": (
                pricing.meters[0].model_copy(
                    update={
                        "rate_parameter_id": "missing",
                    },
                ),
            ),
        },
    )
    with pytest.raises(ValueError, match="coverage"):
        calculate_core_hour_cost(missing, context)


def test_absent_hourly_bill_retains_unknown_residual(tmp_path: Path) -> None:
    """A missing invoice cannot be represented as a zero bill."""
    pricing, context = hourly_inputs(tmp_path)
    records = context.ledger.qualifications[:-1]
    ledger = context.ledger.model_copy(
        update={
            "qualifications": records,
            "parameter_set": context.ledger.parameter_set.model_copy(
                update={
                    "parameters": tuple(r.parameter for r in records),
                },
            ),
        },
    )
    result = calculate_core_hour_cost(
        pricing.model_copy(update={"bill_parameter_id": None}),
        replace(context, ledger=ledger),
    )
    require_equal(result.bill_residual, None)
