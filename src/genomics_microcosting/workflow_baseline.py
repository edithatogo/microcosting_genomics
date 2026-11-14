# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Reconcile a recomputed workflow against an explicitly frozen ledger oracle.

An exact match proves agreement with the selected declarations, not independent
source truth, complete economic scope or scientific acceptance. Oracle creation
from this same model is a regression snapshot, not an independent baseline.
"""

import json
import re
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from typing import Literal, Self
lazy from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.workflow_cost import (
    WorkflowCost,
    WorkflowCostInputs,
    calculate_workflow_cost,
)
lazy from genomics_microcosting.parameter_provenance import Digest, NonEmpty

MAX_ORACLE_BYTES = 32 * 1024 * 1024
MAX_OBSERVATIONS = 250_000
RATIONAL = re.compile(r"^-?(?:0|[1-9][0-9]{0,127})(?:/[1-9][0-9]{0,127})?$")


class _Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class BaselineObservation(_Model):
    """Keep an exact rational, categorical state or explicit unknown."""

    path: tuple[NonEmpty, ...] = Field(min_length=1, max_length=8)
    unit: NonEmpty
    value: str | None

    @model_validator(mode="after")
    def check_value(self) -> Self:
        """Bound numeric parsing and require canonical rational spelling."""
        if (
            self.value is not None
            and self.unit != "state"
            and (
                not RATIONAL.fullmatch(self.value)
                or str(Fraction(self.value)) != self.value
            )
        ):
            msg = "Baseline numeric value must be a bounded canonical rational"
            raise ValueError(msg)
        return self


class FrozenWorkflowBaseline(_Model):
    """Pin a declared oracle to exact input and source identities."""

    format_version: Literal["workflow-baseline-v1"]
    baseline_id: NonEmpty
    workbook_sha256: Digest
    process_graph_sha256: Digest
    parameter_version_id: NonEmpty
    workflow_cost_input_sha256: Digest
    evidence_state: Literal["assumed", "reported", "source_derived", "observed"]
    source_locator: NonEmpty
    scope_limit: NonEmpty
    observations: tuple[BaselineObservation, ...] = Field(
        min_length=1,
        max_length=MAX_OBSERVATIONS,
    )

    @model_validator(mode="after")
    def unique_paths(self) -> Self:
        """Reject duplicate expectations that hide missing coverage."""
        if len({o.path for o in self.observations}) != len(self.observations):
            msg = "Duplicate baseline observation path"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class BaselineDifference:
    """Retain both values; a missing metric value is never zero."""

    path: tuple[str, ...]
    unit: str
    expected: str | None
    actual: str | None


@dataclass(frozen=True)
class WorkflowBaselineReconciliation:
    """Keep source identity, exact differences and all recomputed ledgers."""

    input_sha256: str
    oracle_sha256: str
    oracle: FrozenWorkflowBaseline
    cost: WorkflowCost
    observations: tuple[BaselineObservation, ...]
    differences: tuple[BaselineDifference, ...]
    matches_declared_oracle: bool
    scope: Literal["declared_ledger_projection_only"]


def workflow_baseline_projection(
    cost: WorkflowCost,
) -> tuple[BaselineObservation, ...]:
    """Project declared costs, capacity, pack balances, cases and run outputs.

    This projection does not verify caller-supplied cost objects. Reconciliation
    always recomputes from original inputs. Capturing this projection as its own
    expected output is not independent evidence.

    Args:
        cost: An explicitly selected declared-component cost result.

    Returns:
        Exact observations with separate units and unknown states.

    Raises:
        ValueError: Observation count or rational parsing bounds are exceeded.

    """
    observations: list[BaselineObservation] = []

    def add(
        path: tuple[str, ...],
        unit: str,
        value: Fraction | int | str | None,
    ) -> None:
        if len(observations) >= MAX_OBSERVATIONS:
            msg = "Workflow baseline projection exceeds observation bound"
            raise ValueError(msg)
        observations.append(
            BaselineObservation(
                path=path,
                unit=unit,
                value=None if value is None else str(value),
            ),
        )

    currency = cost.pricing.currency
    for name in (
        "allocated_resource_value",
        "idle_capacity_value",
        "selected_idle_cost",
        "selected_resource_cost",
        "fixed_cost",
        "selected_material_cost",
        "total_selected_cost",
        "unit_cost_per_requested_test",
    ):
        unit = (
            f"{currency}/requested_test"
            if name == "unit_cost_per_requested_test"
            else currency
        )
        add(("cost", name), unit, getattr(cost, name))
    add(
        ("service", "worst_turnaround_seconds"),
        "s",
        cost.worst_turnaround_seconds,
    )
    add(("service", "coverage"), "state", cost.service_coverage)
    add(
        ("service", "eligible"),
        "state",
        str(cost.eligible_for_comparison).lower(),
    )
    inventory = cost.material.inventory
    schedule = inventory.schedule
    add(("service", "feasibility"), "state", schedule.feasibility)
    add(("service", "termination_reason"), "state", schedule.termination_reason)
    add(("material", "status"), "state", inventory.material_status)
    for name in (
        "consumed_stock_value",
        "expired_stock_value",
        "discarded_stock_value",
        "closing_usable_value",
        "closing_unqualified_value",
        "not_received_value",
        "declared_remaining_value",
    ):
        add(("material", name), currency, getattr(cost.material, name))
    lines = {r.resource_id: r for r in cost.resource_lines}
    for resource in schedule.resources:
        prefix = ("resource", resource.resource_id)
        for name in (
            "available_unit_seconds",
            "allocated_unit_seconds",
            "idle_unit_seconds",
        ):
            add(
                (*prefix, name),
                f"{resource.capacity_unit}_s",
                getattr(resource, name),
            )
        add(
            (*prefix, "utilization_fraction"),
            "1",
            resource.utilization_fraction,
        )
        line = lines[resource.resource_id]
        add((*prefix, "basis"), "state", line.basis)
        for name in (
            "allocated_resource_value",
            "idle_capacity_value",
            "selected_cost",
        ):
            add((*prefix, name), currency, getattr(line, name))
    _append_material_service(cost, add)
    _append_issues_reservations(cost, add)
    return tuple(sorted(observations, key=lambda o: o.path))


def _append_material_service(
    cost: WorkflowCost,
    add: Callable[[tuple[str, ...], str, Fraction | int | str | None], None],
) -> None:
    inventory = cost.material.inventory
    schedule = inventory.schedule
    currency = cost.pricing.currency
    items = {item.item_id: item for item in inventory.stock.items}
    for pack in inventory.packs:
        for name in (
            "source_units",
            "consumed_units",
            "expired_units",
            "discarded_units",
            "closing_usable_units",
            "closing_unqualified_units",
            "not_received_units",
        ):
            add(
                ("pack", pack.pack_id, name),
                items[pack.item_id].unit_label,
                getattr(pack, name),
            )
    for case in schedule.cases:
        add(("case", case.case_id, "state"), "state", case.state)
        add(
            ("case", case.case_id, "complete_seconds"),
            "s",
            case.complete_seconds,
        )
        add(
            ("case", case.case_id, "turnaround_seconds"),
            "s",
            case.turnaround_seconds,
        )
        add(
            ("case", case.case_id, "turnaround_violation"),
            "state",
            str(case.turnaround_violation).lower(),
        )
    for run in schedule.runs:
        for name in ("ready_seconds", "start_seconds", "complete_seconds"):
            add(("run", run.operation_id, name), "s", getattr(run, name))
        for name in ("control_slots", "unused_slots"):
            add(("run", run.operation_id, name), "slot", getattr(run, name))
    reportable = cost.reportable_cost
    if reportable is not None:
        add(("reportable", "count"), "result", reportable.declared_result_count)
        add(("reportable", "count_state"), "state", reportable.count_state)
        add(("reportable", "service_scope"), "state", reportable.service_scope)
        add(
            ("reportable", "unit_cost"),
            f"{currency}/declared_result",
            reportable.unit_cost_per_declared_reportable_result,
        )


def _append_issues_reservations(
    cost: WorkflowCost,
    add: Callable[[tuple[str, ...], str, Fraction | int | str | None], None],
) -> None:
    inventory = cost.material.inventory
    items = {item.item_id: item for item in inventory.stock.items}
    resources = {r.resource_id: r for r in inventory.schedule.resources}
    for issue in inventory.issues:
        prefix = (
            "issue",
            issue.operation_id,
            issue.stage_id,
            issue.item_id,
            str(issue.issue_seconds),
        )
        for name in ("required_units", "supplied_units", "unfilled_units"):
            add(
                (*prefix, name),
                items[issue.item_id].unit_label,
                getattr(issue, name),
            )
    for reservation in inventory.schedule.reservations:
        prefix = (
            "reservation",
            reservation.operation_id,
            reservation.role_id,
            reservation.resource_id,
        )
        for name in ("start_seconds", "complete_seconds"):
            add((*prefix, name), "s", getattr(reservation, name))
        add(
            (*prefix, "units"),
            resources[reservation.resource_id].capacity_unit,
            reservation.units,
        )


def _unique_json(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            msg = "Duplicate baseline JSON key"
            raise ValueError(msg)
        result[name] = value
    return result


def reconcile_workflow_baseline(
    inputs: WorkflowCostInputs,
    oracle_payload: bytes,
    oracle_sha256: str,
) -> WorkflowBaselineReconciliation:
    """Compare recomputed declared ledgers with exact, complete oracle coverage.

    Args:
        inputs: Original workflow/stock and independent numeric price contexts.
        oracle_payload: Explicitly selected frozen baseline JSON bytes.
        oracle_sha256: Independently supplied hash of those exact bytes.

    Returns:
        Every actual observation and exact discrepancies, without tolerances.

    Raises:
        ValueError: Source identity, numeric source checks, input identity,
            coverage, units or oracle format fails.
        OSError: An existing price verifier cannot read its selected source.

    """
    digest = sha256(oracle_payload).hexdigest()
    if len(oracle_payload) > MAX_ORACLE_BYTES or digest != oracle_sha256:
        msg = "Baseline oracle size or source hash mismatch"
        raise ValueError(msg)
    oracle = FrozenWorkflowBaseline.model_validate(
        json.loads(oracle_payload, object_pairs_hook=_unique_json),
    )
    cost = calculate_workflow_cost(inputs)
    schedule = cost.material.inventory.schedule
    if (
        oracle.workflow_cost_input_sha256 != cost.input_sha256
        or oracle.workbook_sha256 != cost.material.inventory.stock.baseline_sha256
        or oracle.process_graph_sha256 != schedule.process_graph_sha256
        or oracle.parameter_version_id != schedule.parameter_version_id
    ):
        msg = "Frozen baseline model input identity mismatch"
        raise ValueError(msg)
    observations = workflow_baseline_projection(cost)
    expected = {o.path: o for o in oracle.observations}
    actual = {o.path: o for o in observations}
    if len(actual) != len(observations) or expected.keys() != actual.keys():
        msg = "Frozen baseline observation coverage differs"
        raise ValueError(msg)
    if any(expected[p].unit != actual[p].unit for p in actual):
        msg = "Frozen baseline observation unit mismatch"
        raise ValueError(msg)
    differences = tuple(
        BaselineDifference(
            p,
            actual[p].unit,
            expected[p].value,
            actual[p].value,
        )
        for p in sorted(actual)
        if expected[p].value != actual[p].value
    )
    identity = {
        "format_version": "workflow-baseline-v1",
        "oracle_sha256": digest,
        "workflow_cost_input_sha256": cost.input_sha256,
    }
    return WorkflowBaselineReconciliation(
        sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest(),
        digest,
        oracle,
        cost,
        observations,
        differences,
        not differences,
        "declared_ledger_projection_only",
    )
