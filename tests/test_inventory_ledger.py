# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Expiry, partial packs, controls and prices conserve stock."""

import json
from dataclasses import replace
from datetime import date
from fractions import Fraction
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.compute_cost import ComputeCostContext
from genomics_microcosting.inventory_ledger import (
    InventoryInputs,
    InventoryPlan,
    InventoryPricing,
    WorkflowInputs,
    assess_inventory,
    value_inventory,
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
from tests.test_workflow_schedule import workflow_inputs


def inventory_inputs() -> InventoryInputs:
    """Provide two explicit packs and member/control demand on modeled runs."""
    graph, workload, policy, scenario = workflow_inputs()
    stock = {
        "format_version": "inventory-stock-json-v1",
        "source_id": "stock1",
        "exporter_version": "synthetic-v1",
        "evidence_state": "assumed",
        "scope_limit": "Two synthetic packs only",
        "time_origin_id": "origin1",
        "baseline_sha256": "c" * 64,
        "items": [
            {
                "item_id": "kit",
                "unit_label": "reaction",
                "pack_capacity": 4,
                "sharing_policy": "known_open_life",
                "open_life_seconds": "2",
            },
        ],
        "packs": [
            {
                "pack_id": name,
                "lot_id": name,
                "item_id": "kit",
                "arrived_seconds": "0",
                "sealed_expiry_seconds": "100",
                "opening_state": "sealed",
                "opened_seconds": None,
                "remaining_units": 4,
            }
            for name in ["A", "B"]
        ],
    }
    payload = json.dumps(stock).encode()
    plan = InventoryPlan.model_validate(
        {
            "format_version": "inventory-allocation-v1",
            "policy_id": "material1",
            "parameter_version_id": "v1",
            "baseline_sha256": "c" * 64,
            "process_graph_sha256": workload.process_graph_sha256,
            "stock_source_sha256": sha256(payload).hexdigest(),
            "time_origin_id": "origin1",
            "scope": "declared_materials_only",
            "assumption_basis": "Toy issue/shelf-life rules; unqualified",
            "rules": [
                {
                    "rule_id": kind,
                    "stage_id": "prepare",
                    "item_id": "kit",
                    "unit_label": "reaction",
                    "driver": kind,
                    "units_per_driver": 1,
                    "issue_offset_seconds": "0",
                }
                for kind in ["per_member", "per_control"]
            ],
        },
    )
    return InventoryInputs(
        WorkflowInputs(graph, workload, policy, scenario),
        payload,
        plan,
    )


def restock(inputs: InventoryInputs, stock: object) -> InventoryInputs:
    """Rebind a deliberately changed synthetic source to its exact bytes."""
    payload = json.dumps(stock).encode()
    return InventoryInputs(
        inputs.workflow,
        payload,
        inputs.plan.model_copy(
            update={
                "stock_source_sha256": sha256(payload).hexdigest(),
            },
        ),
    )


def test_open_expiry_controls_and_member_demand_conserve_stock() -> None:
    """Two rule components form one issue; opened remnants expire explicitly."""
    inputs = inventory_inputs()
    result = assess_inventory(inputs)
    checks.require_equal(
        tuple(issue.required_units for issue in result.issues),
        (2, 2),
    )
    checks.require_equal(
        tuple(issue.unfilled_units for issue in result.issues),
        (0, 0),
    )
    checks.require_equal(sum(p.consumed_units for p in result.packs), 4)
    checks.require_equal(sum(p.expired_units for p in result.packs), 4)
    checks.require_equal(sum(p.discarded_units for p in result.packs), 0)
    checks.require_equal(result.material_status, "fulfilled")
    for pack in result.packs:
        checks.require_equal(
            pack.source_units,
            pack.consumed_units
            + pack.expired_units
            + pack.discarded_units
            + pack.closing_usable_units
            + pack.closing_unqualified_units
            + pack.not_received_units,
        )
    checks.require_equal(assess_inventory(inputs), result)


def test_expiry_at_issue_is_unusable_and_unknown_expiry_is_not_infinite() -> None:
    """Keep unknown/expired stock out of usable supply."""
    inputs = inventory_inputs()
    stock = json.loads(inputs.stock_payload)
    stock["packs"][0]["sealed_expiry_seconds"] = None
    result = assess_inventory(restock(inputs, stock))
    checks.require_equal(result.material_status, "unfilled")
    checks.require_equal(result.issues[-1].unfilled_units, 2)
    checks.require_equal(result.packs[0].closing_unqualified_units, 4)
    stock["packs"] = stock["packs"][1:]
    stock["items"][0]["open_life_seconds"] = "3"
    result = assess_inventory(restock(inputs, stock))
    checks.require_equal(result.issues[-1].unfilled_units, 2)
    checks.require_equal(result.packs[0].expired_units, 2)


def test_single_issue_discard_does_not_mean_zero_or_infinite_shelf_life() -> None:
    """Discard single-use leftovers after the combined issue."""
    inputs = inventory_inputs()
    stock = json.loads(inputs.stock_payload)
    stock["items"][0].update(
        {"sharing_policy": "discard_after_issue", "open_life_seconds": None},
    )
    result = assess_inventory(restock(inputs, stock))
    checks.require_equal(sum(p.consumed_units for p in result.packs), 4)
    checks.require_equal(sum(p.discarded_units for p in result.packs), 4)
    checks.require_equal(sum(p.expired_units for p in result.packs), 0)
    checks.require_equal(result.material_status, "fulfilled")
    stock["items"][0]["sharing_policy"] = "known_open_life"
    result = assess_inventory(restock(inputs, stock))
    checks.require_equal(result.material_status, "unfilled")
    checks.require_equal(
        sum(p.closing_unqualified_units for p in result.packs),
        8,
    )


def test_initial_open_packs_and_future_receipts_are_not_new_consumption() -> None:
    """Retain prior depletion and future receipts separately."""
    inputs = inventory_inputs()
    stock = json.loads(inputs.stock_payload)
    stock["packs"][0].update(
        {
            "arrived_seconds": "-2",
            "opening_state": "opened",
            "opened_seconds": "-1",
            "remaining_units": 2,
        },
    )
    stock["packs"].append(
        {
            **stock["packs"][1],
            "pack_id": "C",
            "lot_id": "C",
            "arrived_seconds": "20",
        },
    )
    result = assess_inventory(restock(inputs, stock))
    checks.require_equal(result.packs[0].source_units, 2)
    checks.require_equal(sum(p.consumed_units for p in result.packs), 4)
    checks.require_equal(result.packs[-1].not_received_units, 4)


def price_inputs(tmp_path: Path) -> tuple[InventoryPricing, ComputeCostContext]:
    """Bind synthetic prices to source bytes and validity."""
    params: list[Parameter] = []
    quals: list[ParameterQualification] = []
    validity: list[SourceValidity] = []
    paths: dict[str, Path] = {}
    bindings: list[dict[str, str]] = []
    for lot, value in [("A", "8"), ("B", "12")]:
        path = tmp_path / (lot + ".txt")
        path.write_text(value + "\n", encoding="utf-8")
        digest = sha256(path.read_bytes()).hexdigest()
        source = SourceRecord(
            source_id=lot,
            sha256=digest,
            edition="synthetic",
            locator="line 1",
            limitations="Not a real price",
        )
        parameter = Parameter(
            parameter_id=lot,
            raw_value=value,
            derived_value=value,
            unit="AUD/pack:kit",
            source_sha256=digest,
            source_locator="line 1",
            transformation="identity",
            uncertainty="synthetic",
            status="reported",
        )
        params.append(parameter)
        quals.append(
            ParameterQualification(
                parameter=parameter,
                source=source,
                exact_support=value,
                dimensional_basis="AUD/pack:kit",
                applicability="synthetic",
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
        paths[lot] = path
        bindings.append({"item_id": "kit", "lot_id": lot, "parameter_id": lot})
    context = ComputeCostContext(
        QualificationLedger(
            parameter_set=ParameterSet(
                version_id="v1",
                workbook_sha256="c" * 64,
                parameters=tuple(params),
            ),
            qualifications=tuple(quals),
        ),
        paths,
        tuple(validity),
        date(2026, 11, 7),
    )
    pricing = InventoryPricing.model_validate(
        {
            "format_version": "inventory-value-v1",
            "currency": "AUD",
            "price_year": 2026,
            "tax_basis": "exclusive",
            "bindings": bindings,
        },
    )
    return pricing, context


def test_source_checked_stock_value_is_consumption_not_all_pack_purchases(
    tmp_path: Path,
) -> None:
    """Lot-specific unit values conserve consumed, expired and closing stock."""
    inputs = inventory_inputs()
    pricing, context = price_inputs(tmp_path)
    result = value_inventory(inputs, pricing, context)
    checks.require_equal(result.consumed_stock_value, Fraction(10))
    checks.require_equal(result.expired_stock_value, Fraction(10))
    checks.require_equal(result.declared_remaining_value, Fraction(20))
    checks.require_equal(result.closing_usable_value, Fraction(0))
    checks.require_equal(result.cost_scope, "declared_materials_only")
    context.snapshots["A"].write_text("9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        value_inventory(inputs, pricing, context)


def test_sharing_preserves_unconsumed_stock_value(tmp_path: Path) -> None:
    """Closing stock is retained, not expensed as if every pack were used."""
    inputs = inventory_inputs()
    stock = json.loads(inputs.stock_payload)
    stock["items"][0]["open_life_seconds"] = "100"
    pricing, context = price_inputs(tmp_path)
    result = value_inventory(restock(inputs, stock), pricing, context)
    checks.require_equal(result.consumed_stock_value, Fraction(8))
    checks.require_equal(result.closing_usable_value, Fraction(12))
    checks.require_equal(result.expired_stock_value, Fraction(0))
    checks.require_equal(result.declared_remaining_value, Fraction(20))


def test_fefo_uses_expiry_not_price_or_source_order() -> None:
    """The earlier-expiring eligible pack is selected even if listed second."""
    inputs = inventory_inputs()
    stock = json.loads(inputs.stock_payload)
    stock["packs"][1]["sealed_expiry_seconds"] = "2"
    result = assess_inventory(restock(inputs, stock))
    consumed = [e.pack_id for e in result.events if e.kind == "consumed"]
    checks.require_equal(consumed, ["B", "A"])
    checks.require_equal(
        [e.classified_at_seconds for e in result.events],
        sorted(e.classified_at_seconds for e in result.events),
    )
    first = next(
        e
        for e in result.events
        if e.kind == "consumed" and e.operation_id == "preparec1"
    )
    checks.require_equal(first.pack_id, "B")


def test_arrival_at_issue_is_available_and_zero_runs_leave_stock() -> None:
    """Receipt ties precede issues; no modeled runs means no consumption."""
    inputs = inventory_inputs()
    stock = json.loads(inputs.stock_payload)
    stock["packs"][0]["arrived_seconds"] = "3"
    result = assess_inventory(restock(inputs, stock))
    checks.require_equal(result.material_status, "fulfilled")
    checks.require_equal(result.issues[-1].supplied_units, 2)
    w = inputs.workflow
    empty = InventoryInputs(
        WorkflowInputs(
            w.graph_payload,
            w.workload.model_copy(update={"cases": ()}),
            w.policy,
            w.scenario.model_copy(update={"operations": ()}),
        ),
        inputs.stock_payload,
        inputs.plan,
    )
    result = assess_inventory(empty)
    checks.require_equal(result.issues, ())
    checks.require_equal(sum(p.closing_usable_units for p in result.packs), 8)
    checks.require_equal(sum(p.consumed_units for p in result.packs), 0)


def test_failed_run_retry_and_cancellation_material_footprints() -> None:
    """Retain failed/active issues and skip cancelled future work."""
    inputs = inventory_inputs()
    w = inputs.workflow
    data = w.scenario.model_dump(mode="json")
    data["operations"][0]["members"][0]["outcome"] = "failed"
    data["operations"][2]["dependencies"] = ["retry-c1"]
    data["operations"].append(
        {
            "operation_id": "retry-c1",
            "stage_id": "prepare",
            "members": [{"case_id": "c1", "ordinal": 2, "outcome": "passed"}],
            "release_seconds": "0",
            "dependencies": ["preparec1"],
        },
    )
    scenario = type(w.scenario).model_validate(data)
    changed = InventoryInputs(
        WorkflowInputs(w.graph_payload, w.workload, w.policy, scenario),
        inputs.stock_payload,
        inputs.plan,
    )
    result = assess_inventory(changed)
    checks.require_equal(sum(i.required_units for i in result.issues), 6)
    checks.require_equal(result.issues[-1].unfilled_units, 2)
    checks.require_equal(result.material_status, "unfilled")
    for time, expected in [("0", 2), ("2", 4)]:
        data = w.scenario.model_dump(mode="json")
        data["cancellations"] = [{"case_id": "c1", "at_seconds": time}]
        scenario = type(w.scenario).model_validate(data)
        changed = InventoryInputs(
            WorkflowInputs(w.graph_payload, w.workload, w.policy, scenario),
            inputs.stock_payload,
            inputs.plan,
        )
        result = assess_inventory(changed)
        checks.require_equal(
            sum(i.required_units for i in result.issues),
            expected,
        )


@pytest.mark.parametrize(
    "kind",
    [
        "hash",
        "duplicate",
        "partial_sealed",
        "unit",
        "late_issue",
        "duplicate_rule",
    ],
)
def test_invalid_stock_and_rules_fail_closed(kind: str) -> None:
    """Reject ambiguous packs, units and duplicated drivers."""
    inputs = inventory_inputs()
    stock = json.loads(inputs.stock_payload)
    plan = inputs.plan.model_dump(mode="json")
    if kind == "hash":
        inputs = InventoryInputs(
            inputs.workflow,
            inputs.stock_payload + b"\n",
            inputs.plan,
        )
    elif kind == "duplicate":
        stock["packs"].append(stock["packs"][0])
        inputs = restock(inputs, stock)
    elif kind == "partial_sealed":
        stock["packs"][0]["remaining_units"] = 2
        inputs = restock(inputs, stock)
    elif kind == "unit":
        plan["rules"][0]["unit_label"] = "microlitre"
    elif kind == "late_issue":
        plan["rules"][0]["issue_offset_seconds"] = "4"
    else:
        plan["rules"].append({**plan["rules"][0], "rule_id": "alias"})
    if kind in ("unit", "late_issue", "duplicate_rule"):
        inputs = InventoryInputs(
            inputs.workflow,
            inputs.stock_payload,
            InventoryPlan.model_validate(plan),
        )
    with pytest.raises(ValueError, match=r"hash|Duplicate|capacity|rule"):
        assess_inventory(inputs)


@pytest.mark.parametrize("kind", ["currency", "coverage", "expired_date"])
def test_price_units_coverage_and_validity_are_required(
    tmp_path: Path,
    kind: str,
) -> None:
    """Reject missing rates and incompatible price bases."""
    inputs = inventory_inputs()
    pricing, context = price_inputs(tmp_path)
    if kind == "currency":
        pricing = pricing.model_copy(update={"currency": "USD"})
    elif kind == "coverage":
        pricing = pricing.model_copy(update={"bindings": pricing.bindings[:1]})
    else:
        context = replace(context, costing_date=date(2027, 1, 1))
    with pytest.raises(ValueError, match=r"units|coverage|costing date"):
        value_inventory(inputs, pricing, context)


def test_initial_remaining_and_future_value_are_not_current_consumption(
    tmp_path: Path,
) -> None:
    """Pre-horizon depletion and future receipts stay outside consumed value."""
    inputs = inventory_inputs()
    stock = json.loads(inputs.stock_payload)
    stock["packs"][0].update(
        {
            "arrived_seconds": "-2",
            "opening_state": "opened",
            "opened_seconds": "-1",
            "remaining_units": 2,
        },
    )
    stock["packs"][1]["arrived_seconds"] = "20"
    pricing, context = price_inputs(tmp_path)
    result = value_inventory(restock(inputs, stock), pricing, context)
    checks.require_equal(result.declared_remaining_value, Fraction(16))
    checks.require_equal(result.consumed_stock_value, Fraction(4))
    checks.require_equal(result.not_received_value, Fraction(12))
    checks.require_equal(result.inventory.material_status, "unfilled")


def test_small_pack_sharing_and_discard_oracle() -> None:
    """Independent ceiling arithmetic checks sixty constant, no-expiry cases."""
    inputs = inventory_inputs()
    for sharing in ("known_open_life", "discard_after_issue"):
        for capacity in range(1, 7):
            for driver_units in range(1, 6):
                stock = json.loads(inputs.stock_payload)
                stock["items"][0].update(
                    {
                        "pack_capacity": capacity,
                        "sharing_policy": sharing,
                        "open_life_seconds": "1000",
                    },
                )
                stock["packs"] = [
                    {
                        **stock["packs"][0],
                        "pack_id": f"pack{i}",
                        "remaining_units": capacity,
                    }
                    for i in range(32)
                ]
                changed = restock(inputs, stock)
                plan = changed.plan.model_copy(
                    update={
                        "rules": tuple(
                            r.model_copy(
                                update={"units_per_driver": driver_units},
                            )
                            for r in changed.plan.rules
                        ),
                    },
                )
                changed = InventoryInputs(
                    changed.workflow,
                    changed.stock_payload,
                    plan,
                )
                result = assess_inventory(changed)
                demand = 4 * driver_units
                opened = sum(e.kind == "opened" for e in result.events)
                expected = (
                    (demand + capacity - 1) // capacity
                    if sharing == "known_open_life"
                    else 2 * ((2 * driver_units + capacity - 1) // capacity)
                )
                checks.require_equal(opened, expected)
                checks.require_equal(
                    sum(p.consumed_units for p in result.packs),
                    demand,
                )
                checks.require_equal(
                    sum(p.expired_units for p in result.packs),
                    0,
                )
                checks.require_equal(result.material_status, "fulfilled")


@pytest.mark.parametrize("state", ["unknown", "opened"])
def test_missing_opening_time_cannot_become_fresh_sealed_stock(
    state: str,
) -> None:
    """Keep unknown opening history unqualified."""
    inputs = inventory_inputs()
    stock = json.loads(inputs.stock_payload)
    stock["packs"][0]["opening_state"] = state
    result = assess_inventory(restock(inputs, stock))
    checks.require_equal(result.packs[0].consumed_units, 0)
    checks.require_equal(result.packs[0].closing_unqualified_units, 4)
    checks.require_equal(result.issues[-1].unfilled_units, 2)
