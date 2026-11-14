# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Evaluate finite assumed joint workflow realizations with fixed economics."""

import json
import sys
from bisect import bisect_right
from dataclasses import dataclass, replace
from fractions import Fraction
from hashlib import sha256
from itertools import accumulate
from typing import Literal, Self
lazy from decimal import Decimal
lazy from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.inventory_ledger import (
    InventoryPlan,
    StockSnapshot,
    WorkflowInputs,
)
from genomics_microcosting.workflow_cost import (
    WorkflowCost,
    WorkflowCostInputs,
    calculate_workflow_cost,
)
from genomics_microcosting.workflow_schedule import (
    ResourceSchedulePolicy,
    ReworkScenario,
    StageTiming,
    WorkflowScenario,
)
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.batch_uncertainty import CaseArrival
lazy from genomics_microcosting.dynamic_batch import AvailabilityWindow
lazy from genomics_microcosting.parameter_provenance import NonEmpty

RESULT_VERSION = "joint-workflow-uncertainty-v1"
MAX_STATES = 256
MAX_DRAWS = 10000
MAX_SEED = 2**64 - 1


class _Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class ResourceCalendarState(_Model):
    """Vary a fixed resource's availability without changing capacity or role."""

    resource_id: NonEmpty
    windows: tuple[AvailabilityWindow, ...]


class JointWorkflowState(_Model):
    """Keep arrivals, timing, calendars, stock and scripted outcomes correlated."""

    state_id: NonEmpty
    weight: int = Field(strict=True, gt=0, le=2**31 - 1)
    arrivals: tuple[CaseArrival, ...]
    timings: tuple[StageTiming, ...]
    calendars: tuple[ResourceCalendarState, ...]
    scenario: WorkflowScenario | ReworkScenario
    stock: StockSnapshot


class JointWorkflowEnsemble(_Model):
    """An explicitly assumed finite distribution, not inferred probabilities."""

    format_version: Literal["joint-workflow-ensemble-v1"]
    evidence_state: Literal["assumed"]
    assumption_basis: NonEmpty
    states: tuple[JointWorkflowState, ...] = Field(
        min_length=1,
        max_length=MAX_STATES,
    )

    @model_validator(mode="after")
    def unique_states(self) -> Self:
        """Reject ambiguous joint-state identities."""
        if len({s.state_id for s in self.states}) != len(self.states):
            msg = "Duplicate workflow uncertainty state"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class WorkflowStateOutcome:
    """Retain every realized resource, stock, cost and turnaround result."""

    state_id: str
    weight: int
    cost: WorkflowCost


@dataclass(frozen=True)
class ResourceUncertaintySummary:
    """Keep a weighted mean of ratios distinct from a ratio of weighted totals."""

    resource_id: str
    mean_utilization: Fraction | None
    pooled_utilization: Fraction | None


@dataclass(frozen=True)
class WorkflowUncertaintyResult:
    """Separate exact finite-state summaries from reproducible sampled indices."""

    format_version: Literal["joint-workflow-uncertainty-v1"]
    input_sha256: str
    recipe_sha256: str
    seed: int
    runtime: str
    outcomes: tuple[WorkflowStateOutcome, ...]
    draw_indices: tuple[int, ...]
    full_service_probability: Fraction
    material_fulfilled_probability: Fraction
    eligible_probability: Fraction
    mean_complete_service_cost: Fraction | None
    resources: tuple[ResourceUncertaintySummary, ...]


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate workflow uncertainty JSON field"
            raise ValueError(msg)
        result[key] = value
    return result


def _realize(
    state: JointWorkflowState,
    inputs: WorkflowCostInputs,
) -> WorkflowCostInputs:
    workflow = inputs.inventory.workflow
    workload = Workload.model_validate(workflow.workload)
    policy = ResourceSchedulePolicy.model_validate(workflow.policy)
    arrivals = {a.case_id: a.seconds for a in state.arrivals}
    calendars = {c.resource_id: c.windows for c in state.calendars}
    timings = {t.stage_id: t for t in state.timings}
    if (
        len(arrivals) != len(state.arrivals)
        or arrivals.keys() != {c.case_id for c in workload.cases}
        or len(calendars) != len(state.calendars)
        or calendars.keys() != {r.resource_id for r in policy.resources}
        or len(timings) != len(state.timings)
        or timings.keys() != {t.stage_id for t in policy.timings}
    ):
        msg = "Joint workflow arrival/calendar/timing coverage differs"
        raise ValueError(msg)
    for baseline in policy.timings:
        selected = timings[baseline.stage_id]
        if {(n.role_id, n.resource_id, n.units) for n in selected.needs} != {
            (n.role_id, n.resource_id, n.units) for n in baseline.needs
        }:
            msg = "Joint workflow role/resource/unit scope differs"
            raise ValueError(msg)
    plan = InventoryPlan.model_validate(inputs.inventory.plan)
    if sha256(inputs.inventory.stock_payload).hexdigest() != plan.stock_source_sha256:
        msg = "Joint workflow baseline stock source hash mismatch"
        raise ValueError(msg)
    original = StockSnapshot.model_validate(
        json.loads(
            inputs.inventory.stock_payload,
            parse_float=Decimal,
            object_pairs_hook=_unique_fields,
        ),
    )
    if state.stock.evidence_state != "assumed":
        msg = "Joint workflow stock realizations must be explicitly assumed"
        raise ValueError(msg)
    if (
        state.stock.items != original.items
        or {(p.pack_id, p.item_id, p.lot_id) for p in state.stock.packs}
        != {(p.pack_id, p.item_id, p.lot_id) for p in original.packs}
        or state.stock.baseline_sha256 != original.baseline_sha256
        or state.stock.time_origin_id != original.time_origin_id
    ):
        msg = "Joint workflow stock item/pack/baseline scope differs"
        raise ValueError(msg)
    realized = workload.model_copy(
        update={
            "cases": tuple(
                c.model_copy(update={"arrival_seconds": arrivals[c.case_id]})
                for c in workload.cases
            ),
        },
    )
    selected_policy = policy.model_copy(
        update={
            "timings": tuple(timings[t.stage_id] for t in policy.timings),
            "resources": tuple(
                r.model_copy(update={"windows": calendars[r.resource_id]})
                for r in policy.resources
            ),
        },
    )
    stock_payload = state.stock.model_dump_json().encode()
    inventory = replace(
        inputs.inventory,
        workflow=WorkflowInputs(
            workflow.graph_payload,
            realized,
            selected_policy,
            state.scenario,
        ),
        stock_payload=stock_payload,
        plan=plan.model_copy(
            update={
                "stock_source_sha256": sha256(stock_payload).hexdigest(),
            },
        ),
    )
    return replace(inputs, inventory=inventory)


def _resources(
    outcomes: tuple[WorkflowStateOutcome, ...],
    total: int,
) -> tuple[ResourceUncertaintySummary, ...]:
    rows: dict[str, list[tuple[int, Fraction, Fraction]]] = {}
    for outcome in outcomes:
        for resource in outcome.cost.material.inventory.schedule.resources:
            rows.setdefault(resource.resource_id, []).append(
                (
                    outcome.weight,
                    resource.allocated_unit_seconds,
                    resource.available_unit_seconds,
                ),
            )
    results: list[ResourceUncertaintySummary] = []
    for resource_id, pairs in sorted(rows.items()):
        mean = (
            sum((w * used / available for w, used, available in pairs), Fraction())
            / total
            if all(available for _, _, available in pairs)
            else None
        )
        used = sum((w * value for w, value, _ in pairs), Fraction())
        available = sum((w * value for w, _, value in pairs), Fraction())
        results.append(
            ResourceUncertaintySummary(
                resource_id,
                mean,
                used / available if available else None,
            ),
        )
    return tuple(results)


def simulate_workflow_uncertainty(
    recipe_path: Path,
    inputs: WorkflowCostInputs,
    *,
    seed: int,
    draws: int,
) -> WorkflowUncertaintyResult:
    """Evaluate source-checked joint states then sample declared integer weights.

    Args:
        recipe_path: Exact selected finite distribution of assumed realizations.
        inputs: Fixed source-checked economics, graph, entities and physical scope.
        seed: PCG64 seed; exact runtime/protocol enters the result identity.
        draws: Bounded sample count; exact summaries evaluate every state.

    Returns:
        Full per-state costs, service/material probabilities and resource use.

    Raises:
        ValueError: Invalid scope, source, sampling bounds or modified recipe.
        OSError: Selected recipe or required source cannot be read.

    """
    if (
        type(seed) is not int
        or not 0 <= seed <= MAX_SEED
        or type(draws) is not int
        or not 1 <= draws <= MAX_DRAWS
    ):
        msg = "Invalid workflow sampling seed or draw bound"
        raise ValueError(msg)
    payload = recipe_path.read_bytes()
    digest = sha256(payload).hexdigest()
    ensemble = JointWorkflowEnsemble.model_validate(
        json.loads(
            payload,
            parse_float=Decimal,
            object_pairs_hook=_unique_fields,
        ),
    )
    outcomes = tuple(
        WorkflowStateOutcome(
            s.state_id,
            s.weight,
            calculate_workflow_cost(_realize(s, inputs)),
        )
        for s in ensemble.states
    )
    cumulative = tuple(accumulate(o.weight for o in outcomes))
    total = cumulative[-1]
    rng = np.random.Generator(np.random.PCG64(seed))
    indices = tuple(
        bisect_right(cumulative, int(n)) for n in rng.integers(0, total, size=draws)
    )
    full = sum(
        o.weight
        for o in outcomes
        if o.cost.service_coverage != "partial_requested_tests"
    )
    material = sum(
        o.weight
        for o in outcomes
        if o.cost.material.inventory.material_status == "fulfilled"
    )
    eligible = sum(o.weight for o in outcomes if o.cost.eligible_for_comparison)
    mean = (
        sum((o.weight * o.cost.total_selected_cost for o in outcomes), Fraction())
        / total
        if full == total
        else None
    )
    runtime = f"{sys.version}; NumPy {np.__version__}"
    base = inputs.inventory.workflow
    identity = {
        "function_version": RESULT_VERSION,
        "baseline_stock_sha256": sha256(
            inputs.inventory.stock_payload,
        ).hexdigest(),
        "baseline_workload": Workload.model_validate(
            base.workload,
        ).model_dump(mode="json"),
        "baseline_policy": ResourceSchedulePolicy.model_validate(
            base.policy,
        ).model_dump(mode="json"),
        "baseline_scenario": type(base.scenario)
        .model_validate(
            base.scenario,
        )
        .model_dump(mode="json"),
        "recipe_sha256": digest,
        "seed": seed,
        "draws": draws,
        "runtime": runtime,
        "rng": "numpy.Generator/PCG64/integers",
        "state_cost_inputs": [o.cost.input_sha256 for o in outcomes],
    }
    if sha256(recipe_path.read_bytes()).hexdigest() != digest:
        msg = "Workflow uncertainty recipe changed during execution"
        raise ValueError(msg)
    return WorkflowUncertaintyResult(
        "joint-workflow-uncertainty-v1",
        sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest(),
        digest,
        seed,
        runtime,
        outcomes,
        indices,
        Fraction(full, total),
        Fraction(material, total),
        Fraction(eligible, total),
        mean,
        _resources(outcomes, total),
    )
