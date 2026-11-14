# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Price selected native user/system observations without deriving prices or scope."""

from dataclasses import replace
from decimal import Decimal
lazy from pathlib import Path

import pytest

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    ComputePricing,
    calculate_compute_cost,
)
from tests import checks
from tests.test_compute_cost import inputs
from tests.test_native_usage import native_context, native_payload
lazy from genomics_microcosting.provenance_ledger import (
    Parameter,
    ParameterQualification,
    SourceValidity,
)


def native_inputs(tmp_path: Path) -> tuple[ComputePricing, ComputeCostContext]:
    """Bind two synthetic native counter fields to shared explicit rate/share inputs."""
    pricing, context = inputs(tmp_path)
    payload = native_payload()
    profile = native_context(payload)
    path = tmp_path / "native.json"
    path.write_bytes(payload)
    old = context.ledger.qualifications[0]
    parameters: list[Parameter] = []
    quals: list[ParameterQualification] = []
    periods: list[SourceValidity] = []
    paths = dict(context.snapshots)
    for name, field, value in (
        ("quantity", "user_cpu_seconds", "1.25"),
        ("system", "system_cpu_seconds", "0.25"),
    ):
        source = old.source.model_copy(
            update={
                "source_id": name,
                "sha256": profile.source_sha256,
                "locator": f"wait4:{field}",
            },
        )
        parameter = old.parameter.model_copy(
            update={
                "parameter_id": name,
                "raw_value": value,
                "derived_value": value,
                "source_sha256": profile.source_sha256,
                "source_locator": source.locator,
            },
        )
        parameters.append(parameter)
        quals.append(
            old.model_copy(
                update={
                    "source": source,
                    "parameter": parameter,
                    "exact_support": value,
                },
            ),
        )
        periods.append(context.validity[0].model_copy(update={"source": source}))
        paths[name] = path
    selected = context.ledger.parameter_set.model_copy(
        update={
            "parameters": (*parameters, *context.ledger.parameter_set.parameters[1:]),
        },
    )
    ledger = context.ledger.model_copy(
        update={
            "parameter_set": selected,
            "qualifications": (*quals, *context.ledger.qualifications[1:]),
        },
    )
    context = replace(
        context,
        ledger=ledger,
        snapshots=paths,
        validity=(*periods, *context.validity[1:]),
        native_usage=(profile,),
    )
    meter = pricing.meters[0].model_copy(update={"meter_id": "user"})
    pricing = pricing.model_copy(
        update={
            "meters": (
                meter,
                meter.model_copy(
                    update={
                        "meter_id": "system",
                        "quantity_parameter_id": "system",
                    },
                ),
            ),
        },
    )
    return pricing, context


def test_native_fields_enter_measured_pricing_with_explicit_rates(
    tmp_path: Path,
) -> None:
    """Failed work is still consumed CPU; two nonoverlapping counters reconcile."""
    pricing, context = native_inputs(tmp_path)
    result = calculate_compute_cost(pricing, context)
    checks.require_equal(result.modeled_total, Decimal(3))
    checks.require_equal(result.allocated_cost, Decimal("1.5"))
    checks.require_equal(result.bill_residual, Decimal(22))
    with pytest.raises(ValueError, match="coverage"):
        calculate_compute_cost(pricing, replace(context, native_usage=()))
    wrong = pricing.model_copy(
        update={
            "meters": tuple(
                m.model_copy(
                    update={
                        "usage_basis": "requested",
                        "price_basis": "requested",
                    },
                )
                for m in pricing.meters
            ),
        },
    )
    with pytest.raises(ValueError, match="measured"):
        calculate_compute_cost(wrong, context)
    context.snapshots["quantity"].write_bytes(native_payload() + b" ")
    with pytest.raises(ValueError, match="hash"):
        calculate_compute_cost(pricing, context)


def test_native_quantity_aliases_cannot_price_one_counter_twice(tmp_path: Path) -> None:
    """A new parameter name does not make the same physical observation independent."""
    pricing, context = native_inputs(tmp_path)
    first = context.ledger.qualifications[0]
    alias = first.parameter.model_copy(update={"parameter_id": "alias"})
    ledger = context.ledger.model_copy(
        update={
            "parameter_set": context.ledger.parameter_set.model_copy(
                update={
                    "parameters": (*context.ledger.parameter_set.parameters, alias),
                },
            ),
            "qualifications": (
                *context.ledger.qualifications,
                first.model_copy(update={"parameter": alias}),
            ),
        },
    )
    priced = pricing.model_copy(
        update={
            "meters": (
                *pricing.meters,
                pricing.meters[0].model_copy(
                    update={"meter_id": "alias", "quantity_parameter_id": "alias"},
                ),
            ),
        },
    )
    with pytest.raises(ValueError, match="twice"):
        calculate_compute_cost(priced, replace(context, ledger=ledger))
