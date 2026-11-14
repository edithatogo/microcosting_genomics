# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Frozen baseline comparison cannot conceal component or source mismatches."""

import json
from dataclasses import replace
from hashlib import sha256
from typing import cast
lazy from collections.abc import Callable
lazy from pathlib import Path

import pytest

from genomics_microcosting.inventory_ledger import (
    InventoryInputs,
    WorkflowInputs,
)
from genomics_microcosting.workflow_baseline import reconcile_workflow_baseline
from genomics_microcosting.workflow_cost import (
    WorkflowCostInputs,
    calculate_workflow_cost,
)
from tests import checks
from tests.test_workflow_cost import cost_inputs


def expected_observations() -> list[dict[str, object]]:
    """Specify independent exact toy-schedule and stock-flow arithmetic."""
    rows: list[dict[str, object]] = []

    def add(path: tuple[str, ...], unit: str, value: str | None) -> None:
        rows.append({"path": list(path), "unit": unit, "value": value})

    for name, value in {
        "allocated_resource_value": "18",
        "idle_capacity_value": "42",
        "selected_idle_cost": "0",
        "selected_resource_cost": "18",
        "fixed_cost": "5",
        "selected_material_cost": "10",
        "total_selected_cost": "33",
    }.items():
        add(("cost", name), "AUD", value)
    add(("cost", "unit_cost_per_requested_test"), "AUD/requested_test", "33/2")
    add(("service", "worst_turnaround_seconds"), "s", "9")
    for name, value in {
        "coverage": "all_requested_tests",
        "eligible": "true",
        "feasibility": "feasible",
        "termination_reason": "completed",
    }.items():
        add(("service", name), "state", value)
    add(("material", "status"), "state", "fulfilled")
    for name, value in {
        "consumed_stock_value": "10",
        "expired_stock_value": "10",
        "discarded_stock_value": "0",
        "closing_usable_value": "0",
        "closing_unqualified_value": "0",
        "not_received_value": "0",
        "declared_remaining_value": "20",
    }.items():
        add(("material", name), "AUD", value)
    # Two six-slot-second occupations at rates one/two, available twenty each.
    for name, used, idle in [("staff", "6", "14"), ("instrument", "12", "28")]:
        for field, value in {
            "available_unit_seconds": "20",
            "allocated_unit_seconds": "6",
            "idle_unit_seconds": "14",
        }.items():
            add(("resource", name, field), f"{name}-slots_s", value)
        add(("resource", name, "utilization_fraction"), "1", "3/10")
        add(("resource", name, "basis"), "state", "allocated")
        for field, value in {
            "allocated_resource_value": used,
            "idle_capacity_value": idle,
            "selected_cost": used,
        }.items():
            add(("resource", name, field), "AUD", value)
    append_material_service(add)
    append_issues_reservations(add)
    return rows


def append_material_service(
    add: Callable[[tuple[str, ...], str, str | None], None],
) -> None:
    """Specify the independently calculated two-pack/case/run oracle."""
    # Each four-reaction pack supplies one member and one control, then expires.
    for pack in ["A", "B"]:
        for field, value in {
            "source_units": "4",
            "consumed_units": "2",
            "expired_units": "2",
            "discarded_units": "0",
            "closing_usable_units": "0",
            "closing_unqualified_units": "0",
            "not_received_units": "0",
        }.items():
            add(("pack", pack, field), "reaction", value)
    for name, complete in [("c1", "6"), ("c2", "9")]:
        add(("case", name, "state"), "state", "completed")
        add(("case", name, "complete_seconds"), "s", complete)
        add(("case", name, "turnaround_seconds"), "s", complete)
        add(("case", name, "turnaround_violation"), "state", "false")
    for name, ready, start, complete, controls, unused in [
        ("preparec1", "0", "0", "4", "1", "2"),
        ("preparec2", "0", "3", "7", "1", "2"),
        ("interpretc1", "4", "4", "6", "0", "3"),
        ("interpretc2", "7", "7", "9", "0", "3"),
    ]:
        for field, value in {
            "ready_seconds": ready,
            "start_seconds": start,
            "complete_seconds": complete,
        }.items():
            add(("run", name, field), "s", value)
        add(("run", name, "control_slots"), "slot", controls)
        add(("run", name, "unused_slots"), "slot", unused)
    add(("reportable", "count"), "result", None)
    add(("reportable", "count_state"), "state", "unknown")
    add(("reportable", "service_scope"), "state", "complete_modeled_workload")
    add(("reportable", "unit_cost"), "AUD/declared_result", None)


def append_issues_reservations(
    add: Callable[[tuple[str, ...], str, str | None], None],
) -> None:
    """Retain hand-computed issue quantities and half-open role reservations."""
    for operation, time in [("preparec1", "0"), ("preparec2", "3")]:
        for field, value in {
            "required_units": "2",
            "supplied_units": "2",
            "unfilled_units": "0",
        }.items():
            add(
                ("issue", operation, "prepare", "kit", time, field),
                "reaction",
                value,
            )
    for operation, role, resource, start, complete in [
        ("preparec1", "hands", "staff", "0", "1"),
        ("preparec1", "machine", "instrument", "1", "4"),
        ("preparec2", "hands", "staff", "3", "4"),
        ("preparec2", "machine", "instrument", "4", "7"),
        ("interpretc1", "review", "staff", "4", "6"),
        ("interpretc2", "review", "staff", "7", "9"),
    ]:
        add(
            ("reservation", operation, role, resource, "start_seconds"),
            "s",
            start,
        )
        add(
            ("reservation", operation, role, resource, "complete_seconds"),
            "s",
            complete,
        )
        add(
            ("reservation", operation, role, resource, "units"),
            f"{resource}-slots",
            "1",
        )


def oracle(inputs: WorkflowCostInputs) -> dict[str, object]:
    """Bind manual expectations to the exact toy input."""
    result = calculate_workflow_cost(inputs)
    graph_hash = inputs.inventory.workflow.workload.process_graph_sha256
    return {
        "format_version": "workflow-baseline-v1",
        "baseline_id": "toy-baseline",
        "workbook_sha256": "c" * 64,
        "process_graph_sha256": graph_hash,
        "parameter_version_id": "v1",
        "workflow_cost_input_sha256": result.input_sha256,
        "evidence_state": "assumed",
        "source_locator": "manual toy ledger",
        "scope_limit": "Synthetic; no observed or historical baseline",
        "observations": expected_observations(),
    }


def payload(record: dict[str, object]) -> tuple[bytes, str]:
    """Hash the exact selected oracle bytes."""
    raw = json.dumps(record).encode()
    return raw, sha256(raw).hexdigest()


def observation(
    record: dict[str, object],
    path: list[str],
) -> dict[str, object]:
    """Select a known expected line without changing the component total."""
    rows = cast("list[dict[str, object]]", record["observations"])
    return next(row for row in rows if row["path"] == path)


def test_exact_manual_baseline_reconciles_all_declared_ledgers(
    tmp_path: Path,
) -> None:
    """Reconcile independently specified component values."""
    inputs = cost_inputs(tmp_path)
    raw, digest = payload(oracle(inputs))
    result = reconcile_workflow_baseline(inputs, raw, digest)
    checks.require_equal(result.matches_declared_oracle, expected=True)
    checks.require_equal(result.differences, ())
    checks.require_equal(result.cost, calculate_workflow_cost(inputs))
    checks.require_equal(len(result.observations), len(expected_observations()))
    checks.require_equal(result.oracle.evidence_state, "assumed")
    checks.require_equal(result.scope, "declared_ledger_projection_only")
    checks.require_equal(
        reconcile_workflow_baseline(inputs, raw, digest),
        result,
    )


def test_compensating_resource_errors_do_not_hide_behind_matching_total(
    tmp_path: Path,
) -> None:
    """A total of 33 cannot conceal opposing capacity/cost discrepancies."""
    inputs = cost_inputs(tmp_path)
    record = oracle(inputs)
    for name, cost in [("staff", "7"), ("instrument", "11")]:
        observation(record, ["resource", name, "selected_cost"])["value"] = cost
    result = reconcile_workflow_baseline(inputs, *payload(record))
    checks.require_equal(result.matches_declared_oracle, expected=False)
    checks.require_equal(len(result.differences), 2)
    checks.require_equal({d.expected for d in result.differences}, {"7", "11"})
    checks.require_equal({d.actual for d in result.differences}, {"6", "12"})


@pytest.mark.parametrize("change", ["missing", "extra", "duplicate"])
def test_complete_unique_metric_coverage_is_required(
    tmp_path: Path,
    change: str,
) -> None:
    """A retained total cannot excuse missing, aliased or unknown components."""
    inputs = cost_inputs(tmp_path)
    record = oracle(inputs)
    rows = cast("list[dict[str, object]]", record["observations"])
    if change == "missing":
        rows.pop()
    elif change == "extra":
        rows.append(
            {
                "path": ["resource", "hidden", "selected_cost"],
                "unit": "AUD",
                "value": "0",
            },
        )
    else:
        rows.append(rows[0])
    with pytest.raises(ValueError, match=r"coverage|Duplicate"):
        reconcile_workflow_baseline(inputs, *payload(record))


@pytest.mark.parametrize(
    "field",
    [
        "workbook_sha256",
        "process_graph_sha256",
        "parameter_version_id",
        "workflow_cost_input_sha256",
    ],
)
def test_frozen_input_identity_is_required(tmp_path: Path, field: str) -> None:
    """An oracle for another input cannot be relabelled as the baseline."""
    inputs = cost_inputs(tmp_path)
    record = oracle(inputs)
    record[field] = "wrong" if field == "parameter_version_id" else "a" * 64
    with pytest.raises(ValueError, match="input identity"):
        reconcile_workflow_baseline(inputs, *payload(record))


def test_source_bytes_and_duplicate_json_fields_are_checked(
    tmp_path: Path,
) -> None:
    """Check source identity and unambiguous parsing before arithmetic."""
    inputs = cost_inputs(tmp_path)
    raw, digest = payload(oracle(inputs))
    with pytest.raises(ValueError, match="source hash"):
        reconcile_workflow_baseline(inputs, raw + b" ", digest)
    ambiguous = raw[:-1] + b', "baseline_id":"other"}'
    with pytest.raises(ValueError, match="Duplicate baseline JSON"):
        reconcile_workflow_baseline(
            inputs,
            ambiguous,
            sha256(ambiguous).hexdigest(),
        )


def test_units_are_not_implicitly_converted(tmp_path: Path) -> None:
    """Do not guess a time-unit conversion for an oracle."""
    inputs = cost_inputs(tmp_path)
    record = oracle(inputs)
    observation(record, ["case", "c1", "complete_seconds"])["unit"] = "h"
    with pytest.raises(ValueError, match="unit mismatch"):
        reconcile_workflow_baseline(inputs, *payload(record))


@pytest.mark.parametrize("bad", ["1.0", "2/4", "0/1", "1e999999", "NaN", "1/0"])
def test_numeric_forms_are_exact_and_bounded(tmp_path: Path, bad: str) -> None:
    """Reject rounding, noncanonical rationals and numeric blowups."""
    inputs = cost_inputs(tmp_path)
    record = oracle(inputs)
    observation(record, ["cost", "fixed_cost"])["value"] = bad
    with pytest.raises(ValueError, match="canonical rational"):
        reconcile_workflow_baseline(inputs, *payload(record))


def test_unknown_report_count_does_not_match_zero(tmp_path: Path) -> None:
    """An explicit unknown survives both the model and the comparison report."""
    inputs = cost_inputs(tmp_path)
    record = oracle(inputs)
    observation(record, ["reportable", "count"])["value"] = "0"
    result = reconcile_workflow_baseline(inputs, *payload(record))
    checks.require_equal(result.matches_declared_oracle, expected=False)
    checks.require_equal(result.differences[0].expected, "0")
    checks.require_equal(result.differences[0].actual, None)


def test_model_price_sources_are_reverified(tmp_path: Path) -> None:
    """A frozen oracle cannot authorize stale or altered independent prices."""
    inputs = cost_inputs(tmp_path)
    selected = payload(oracle(inputs))
    (tmp_path / "staff.txt").write_text("9\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"[Ss]ource|[Ss]napshot|[Hh]ash"):
        reconcile_workflow_baseline(inputs, *selected)


def test_oracle_source_identity_binds_semantically_equal_whitespace(
    tmp_path: Path,
) -> None:
    """A different source revision retains a different comparison identity."""
    inputs = cost_inputs(tmp_path)
    raw, digest = payload(oracle(inputs))
    first = reconcile_workflow_baseline(inputs, raw, digest)
    second = reconcile_workflow_baseline(
        inputs,
        raw + b"\n",
        sha256(raw + b"\n").hexdigest(),
    )
    checks.require_equal(first.matches_declared_oracle, expected=True)
    checks.require_equal(second.matches_declared_oracle, expected=True)
    if first.input_sha256 == second.input_sha256:
        pytest.fail("Distinct oracle byte revisions lost their identity")


def test_zero_demand_preserves_fixed_idle_costs_and_undefined_ratios(
    tmp_path: Path,
) -> None:
    """A manually reconciled empty horizon retains 60 idle plus five fixed."""
    inputs = cost_inputs(tmp_path, "available")
    inv = inputs.inventory
    workflow = inv.workflow
    inputs = replace(
        inputs,
        inventory=InventoryInputs(
            WorkflowInputs(
                workflow.graph_payload,
                workflow.workload.model_copy(update={"cases": ()}),
                workflow.policy,
                workflow.scenario.model_copy(update={"operations": ()}),
            ),
            inv.stock_payload,
            inv.plan,
        ),
    )
    record = oracle(inputs)
    rows = cast("list[dict[str, object]]", record["observations"])
    rows[:] = [
        row
        for row in rows
        if cast("list[str]", row["path"])[0]
        not in {"case", "run", "reservation", "issue"}
    ]
    for row in rows:
        path = cast("list[str]", row["path"])
        if path[0] == "resource":
            changes = {
                "basis": "available",
                "allocated_unit_seconds": "0",
                "idle_unit_seconds": "20",
                "utilization_fraction": "0",
                "allocated_resource_value": "0",
                "idle_capacity_value": "20" if path[1] == "staff" else "40",
                "selected_cost": "20" if path[1] == "staff" else "40",
            }
            row["value"] = changes.get(path[-1], row["value"])
        if path[0] == "pack":
            changes = {
                "consumed_units": "0",
                "expired_units": "0",
                "closing_usable_units": "4",
            }
            row["value"] = changes.get(path[-1], row["value"])
    for path, value in [
        (["cost", "allocated_resource_value"], "0"),
        (["cost", "idle_capacity_value"], "60"),
        (["cost", "selected_idle_cost"], "60"),
        (["cost", "selected_resource_cost"], "60"),
        (["cost", "selected_material_cost"], "0"),
        (["cost", "total_selected_cost"], "65"),
        (["cost", "unit_cost_per_requested_test"], None),
        (["service", "worst_turnaround_seconds"], None),
        (["service", "coverage"], "no_demand"),
        (["service", "eligible"], "false"),
        (["reportable", "count"], "0"),
        (["reportable", "count_state"], "zero"),
        (["material", "consumed_stock_value"], "0"),
        (["material", "expired_stock_value"], "0"),
        (["material", "closing_usable_value"], "20"),
    ]:
        observation(record, path)["value"] = value
    result = reconcile_workflow_baseline(inputs, *payload(record))
    checks.require_equal(result.differences, ())
    checks.require_equal(result.matches_declared_oracle, expected=True)
    checks.require_equal(result.cost.total_selected_cost, 65)
