# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify static idle, boundary and pack-cost accounting."""

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
lazy from pathlib import Path

import pytest

from genomics_microcosting.static_batch_cost import (
    BatchPricing,
    calculate_static_batch_cost,
)
from tests import checks
from tests.test_compute_cost import inputs
from tests.test_static_batch import policy, workload
lazy from genomics_microcosting.compute_cost import ComputeCostContext


def batch_inputs(
    tmp_path: Path,
    entity_kind: str = "libraries",
) -> tuple[BatchPricing, ComputeCostContext]:
    """Supply explicit synthetic batch rates with matched units."""
    # Reuse four numeric sources while binding their units to this separate model.
    _, context = inputs(tmp_path)
    units = ("AUD/horizon", f"AUD/{entity_kind}", "AUD/run", "AUD/pack")
    params = tuple(
        p.model_copy(update={"unit": u})
        for p, u in zip(context.ledger.parameter_set.parameters, units, strict=True)
    )
    selected = context.ledger.parameter_set.model_copy(update={"parameters": params})
    quals = tuple(
        q.model_copy(update={"parameter": p, "dimensional_basis": p.unit})
        for q, p in zip(context.ledger.qualifications, params, strict=True)
    )
    context = replace(
        context,
        ledger=context.ledger.model_copy(
            update={"parameter_set": selected, "qualifications": quals},
        ),
    )
    pricing = BatchPricing(
        currency="AUD",
        price_year=2026,
        tax_basis="inclusive",
        fixed_parameter_id="quantity",
        item_parameter_id="rate",
        run_parameter_id="share",
        pack_parameter_id="bill",
        pack_capacity=3,
        pack_scope="per_run",
        pack_driver="occupied_slots",
        assumption_basis="synthetic only",
    )
    return pricing, context


def test_pack_scope_and_idle_cost_are_explicit(tmp_path: Path) -> None:
    """A source-backed synthetic rate ledger drives explicit batch arithmetic."""
    pricing, context = batch_inputs(tmp_path)
    idle = calculate_static_batch_cost(workload(0), policy(), pricing, context)
    checks.require_equal(idle.total_cost, Decimal(10))
    checks.require_equal(idle.idle_cost, Decimal(10))
    checks.require_equal(idle.unit_cost, None)
    result = calculate_static_batch_cost(workload(4), policy(), pricing, context)
    checks.require_equal(result.packs, 3)
    checks.require_equal(result.total_cost, Decimal(94))
    checks.require_equal(result.unit_cost, Fraction(47, 2))
    pooled = calculate_static_batch_cost(
        workload(4),
        policy(),
        pricing.model_copy(update={"pack_scope": "horizon"}),
        context,
    )
    checks.require_equal(pooled.packs, 2)
    checks.require_equal(pooled.total_cost, Decimal(69))
    for demand, expected, packs in (
        (1, Decimal("37.5"), 1),
        (3, Decimal("66.5"), 2),
    ):
        boundary = calculate_static_batch_cost(
            workload(demand),
            policy(),
            pricing,
            context,
        )
        checks.require_equal((boundary.total_cost, boundary.packs), (expected, packs))
        checks.require_equal(
            boundary.pack_units_used + boundary.pack_units_unused,
            packs * 3,
        )
    with pytest.raises(ValueError, match="pack_capacity"):
        calculate_static_batch_cost(
            workload(1),
            policy(),
            pricing.model_copy(update={"pack_capacity": 0}),
            context,
        )
    context.snapshots["bill"].write_text("26\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        calculate_static_batch_cost(workload(1), policy(), pricing, context)
