# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Static batch arithmetic with explicit sourced rates and assumed pack rules."""

import json
from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext
from fractions import Fraction
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    verify_numeric_source_values,
)
from genomics_microcosting.cost_denominators import (
    CostServiceScope,
    ReportableCostSummary,
    summarize_reportable_cost,
)
from genomics_microcosting.dynamic_batch import (
    DynamicBatchPolicy,
    DynamicBatchResult,
    ScheduledRun,
    earliest_batch_start,
    schedule_batches,
)
from genomics_microcosting.static_batch import (
    StaticBatchPolicy,
    plan_static_batches,
    validate_batch_demand,
)
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.parameter_provenance import NonEmpty


class BatchPricing(BaseModel):
    """Declare cost-driver identities and explicit pack-sharing assumptions."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    format_version: Literal["static-batch-cost-v1"] = "static-batch-cost-v1"
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive"]
    fixed_parameter_id: NonEmpty
    item_parameter_id: NonEmpty
    run_parameter_id: NonEmpty
    pack_parameter_id: NonEmpty
    pack_capacity: int = Field(strict=True, gt=0)
    pack_scope: Literal["per_run", "horizon"]
    pack_driver: Literal["payload_slots", "control_slots", "occupied_slots"]
    assumption_basis: NonEmpty


@dataclass(frozen=True)
class StaticBatchCost:
    """Retain driver counts, costs and an exact optional per-demand ratio."""

    input_sha256: str
    total_cost: Decimal
    fixed_cost: Decimal
    item_cost: Decimal
    run_cost: Decimal
    pack_cost: Decimal
    packs: int
    pack_units_used: int
    pack_units_unused: int
    idle_cost: Decimal
    unit_cost: Fraction | None
    demand_count: int
    planned_runs: int
    reportable_cost: ReportableCostSummary | None = None


def calculate_static_batch_cost(
    workload: Workload,
    policy: StaticBatchPolicy,
    pricing: BatchPricing,
    context: ComputeCostContext,
) -> StaticBatchCost:
    """Calculate fixed/variable/run/pack costs without inferring rate validity."""
    workload = Workload.model_validate(workload.model_dump())
    policy = StaticBatchPolicy.model_validate(policy.model_dump())
    pricing = BatchPricing.model_validate(pricing.model_dump())
    plan = plan_static_batches(workload, policy)
    return _price_runs(
        _CostDrivers(
            workload,
            policy,
            pricing,
            context,
            plan.payloads,
            plan.input_sha256,
        ),
    )


@dataclass(frozen=True)
class _CostDrivers:
    workload: Workload
    policy: StaticBatchPolicy
    pricing: BatchPricing
    context: ComputeCostContext
    payloads: tuple[int, ...]
    plan_digest: str
    service_scope: CostServiceScope = "static_projection"


def _price_runs(drivers: _CostDrivers) -> StaticBatchCost:
    rates = _verified_rates(drivers.policy, drivers.pricing, drivers.context)
    return _assemble_cost(drivers, rates)


def _verified_rates(
    policy: StaticBatchPolicy,
    pricing: BatchPricing,
    context: ComputeCostContext,
) -> list[Decimal]:
    values = verify_numeric_source_values(context)
    fields = (
        (pricing.fixed_parameter_id, "horizon"),
        (pricing.item_parameter_id, policy.entity_kind),
        (pricing.run_parameter_id, "run"),
        (pricing.pack_parameter_id, "pack"),
    )
    if {identifier for identifier, _ in fields} != values.keys():
        msg = "Batch rate coverage differs from the selected ledger"
        raise ValueError(msg)
    rates: list[Decimal] = []
    for identifier, unit in fields:
        value, source_unit = values[identifier]
        if value < 0 or source_unit != f"{pricing.currency}/{unit}":
            msg = "Batch rate is negative or has incompatible units"
            raise ValueError(msg)
        rates.append(value)
    return rates


def _pack_units(payload: int, policy: StaticBatchPolicy, pricing: BatchPricing) -> int:
    return {
        "payload_slots": payload,
        "control_slots": policy.controls_per_run,
        "occupied_slots": payload + policy.controls_per_run,
    }[pricing.pack_driver]


def _pack_count(units: int, pricing: BatchPricing) -> int:
    return (units + pricing.pack_capacity - 1) // pricing.pack_capacity


def _assemble_cost(drivers: _CostDrivers, rates: list[Decimal]) -> StaticBatchCost:
    workload, policy, pricing, context = (
        drivers.workload,
        drivers.policy,
        drivers.pricing,
        drivers.context,
    )
    driver_counts = [_pack_units(n, policy, pricing) for n in drivers.payloads]
    used = sum(driver_counts)
    if pricing.pack_scope == "horizon":
        driver_counts = [used]
    packs = sum(_pack_count(n, pricing) for n in driver_counts)
    demand = sum(drivers.payloads)
    with localcontext() as decimal_context:
        decimal_context.prec = 50
        decimal_context.traps[Inexact] = True
        fixed = rates[0]
        item = rates[1] * demand
        run = rates[2] * len(drivers.payloads)
        pack = rates[3] * packs
        total = fixed + item + run + pack
    identity = {
        "plan_digest": drivers.plan_digest,
        "payloads": drivers.payloads,
        "workload": workload.model_dump(mode="json"),
        "policy": policy.model_dump(mode="json"),
        "pricing": pricing.model_dump(mode="json"),
        "ledger": context.ledger.model_dump(mode="json"),
        "validity": [x.model_dump(mode="json") for x in context.validity],
        "costing_date": context.costing_date.isoformat(),
    }
    digest = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    return StaticBatchCost(
        digest,
        total,
        fixed,
        item,
        run,
        pack,
        packs,
        used,
        packs * pricing.pack_capacity - used,
        fixed if demand == 0 else Decimal(0),
        None if demand == 0 else Fraction(total) / demand,
        demand,
        len(drivers.payloads),
        summarize_reportable_cost(
            workload,
            total,
            service_scope=drivers.service_scope,
        ),
    )


@dataclass(frozen=True)
class DynamicBatchCost:
    """Keep dynamic service scope and temporal feasibility with its modeled cost."""

    schedule: DynamicBatchResult
    cost: StaticBatchCost
    cost_state: Literal["complete_workload", "partial_workload"]


def calculate_dynamic_batch_cost(
    workload: Workload,
    policy: DynamicBatchPolicy,
    pricing: BatchPricing,
    context: ComputeCostContext,
) -> DynamicBatchCost:
    """Price only modeled runs while retaining unserved and late workload scope."""
    workload = Workload.model_validate(workload.model_dump())
    policy = DynamicBatchPolicy.model_validate(policy.model_dump())
    pricing = BatchPricing.model_validate(pricing.model_dump())
    schedule = schedule_batches(workload, policy)
    drivers = _CostDrivers(
        workload,
        policy.batch,
        pricing,
        context,
        tuple(len(run.case_ids) for run in schedule.runs),
        schedule.input_sha256,
        "partial_modeled_workload"
        if schedule.unserved_case_ids
        else "complete_modeled_workload",
    )
    cost = _price_runs(drivers)
    return DynamicBatchCost(
        schedule,
        cost,
        "partial_workload" if schedule.unserved_case_ids else "complete_workload",
    )


MAX_VARIABLE_BATCH_REQUESTS = 128


@dataclass(frozen=True)
class VariableBatchPoint:
    """Retain one minimum-cost load plan and its modeled completion times."""

    payloads: tuple[int, ...]
    run_completion_seconds: tuple[Decimal, ...]
    worst_turnaround_seconds: Decimal
    cost: StaticBatchCost


@dataclass(frozen=True)
class VariableBatchSearch:
    """Keep idle cost and infeasibility distinct from a complete frontier."""

    input_sha256: str
    state: Literal["feasible", "infeasible", "no_demand"]
    frontier: tuple[VariableBatchPoint, ...]
    idle_cost: StaticBatchCost | None


def _completion_slots(
    policy: DynamicBatchPolicy,
    arrival: Decimal,
    limit: int,
) -> tuple[Decimal, ...]:
    completions: list[Decimal] = []
    with localcontext() as arithmetic:
        arithmetic.prec = 50
        arithmetic.traps[Inexact] = True
        deadline = arrival + policy.turnaround_limit_seconds
        for window in policy.windows:
            end = min(window.end_seconds, deadline)
            complete = max(window.start_seconds, arrival) + policy.run_duration_seconds
            while complete <= end and len(completions) < limit:
                completions.append(complete)
                if len(completions) == limit:
                    return tuple(completions)
                complete += policy.run_duration_seconds
    return tuple(completions)


def _minimum_pack_loads(
    demand: int,
    slots: int,
    payload_packs: tuple[int, ...],
) -> list[tuple[int, ...]]:
    # For each run count and served total, retain minimum packs and a stable tie.
    states: dict[int, tuple[int, tuple[int, ...]]] = {0: (0, ())}
    complete: list[tuple[int, ...]] = []
    for _ in range(slots):
        next_states: dict[int, tuple[int, tuple[int, ...]]] = {}
        for served, (packs, loads) in states.items():
            for load, extra_packs in enumerate(payload_packs, 1):
                total = served + load
                if total > demand:
                    break
                candidate = (packs + extra_packs, (*loads, load))
                if total not in next_states or candidate < next_states[total]:
                    next_states[total] = candidate
        if demand in next_states:
            complete.append(next_states.pop(demand)[1])
        states = next_states
    return complete


def optimize_variable_batch_runs(
    workload: Workload,
    policy: DynamicBatchPolicy,
    pricing: BatchPricing,
    context: ComputeCostContext,
) -> VariableBatchSearch:
    """Compare feasible variable loads for simultaneous requests.

    Each run starts in the earliest available slot. The turnaround limit,
    calendar, payload bound and controls stay fixed. For each feasible run count
    one minimum-cost plan represents all equivalent load orders.
    """
    workload = Workload.model_validate(workload.model_dump())
    policy = DynamicBatchPolicy.model_validate(policy.model_dump())
    pricing = BatchPricing.model_validate(pricing.model_dump())
    demand = validate_batch_demand(workload, policy.batch)
    if demand > MAX_VARIABLE_BATCH_REQUESTS:
        msg = "Variable batch search demand exceeds its supported bound"
        raise ValueError(msg)
    if policy.max_wait_seconds != 0:
        msg = "Variable batch search requires zero max wait"
        raise ValueError(msg)
    if any(w.end_seconds > workload.horizon_seconds for w in policy.windows):
        msg = "Availability window exceeds workload horizon"
        raise ValueError(msg)
    arrivals = {case.arrival_seconds for case in workload.cases}
    if len(arrivals) > 1 or None in arrivals:
        msg = "Variable batch search requires simultaneous known arrivals"
        raise ValueError(msg)
    arrival = next(iter(arrivals), Decimal(0))
    if arrival is None:
        raise AssertionError
    rates = _verified_rates(policy.batch, pricing, context)
    identity = {
        "format_version": "variable-batch-search-v1",
        "workload": workload.model_dump(mode="json"),
        "policy": policy.model_dump(mode="json"),
        "pricing": pricing.model_dump(mode="json"),
        "ledger": context.ledger.model_dump(mode="json"),
        "validity": [v.model_dump(mode="json") for v in context.validity],
        "costing_date": context.costing_date.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    if demand == 0:
        idle = _assemble_cost(
            _CostDrivers(workload, policy.batch, pricing, context, (), digest),
            rates,
        )
        return VariableBatchSearch(digest, "no_demand", (), idle)
    slots = _completion_slots(policy, arrival, min(demand, policy.batch.max_runs))
    payload_packs = tuple(
        _pack_count(_pack_units(load, policy.batch, pricing), pricing)
        if pricing.pack_scope == "per_run"
        else 0
        for load in range(1, min(demand, policy.batch.payload_limit) + 1)
    )
    frontier: list[VariableBatchPoint] = []
    for payloads in _minimum_pack_loads(demand, len(slots), payload_packs):
        cost = _assemble_cost(
            _CostDrivers(
                workload,
                policy.batch,
                pricing,
                context,
                payloads,
                digest,
                "complete_modeled_workload",
            ),
            rates,
        )
        if frontier and cost.total_cost >= frontier[-1].cost.total_cost:
            continue
        completions = slots[: len(payloads)]
        with localcontext() as arithmetic:
            arithmetic.prec = 50
            arithmetic.traps[Inexact] = True
            turnaround = completions[-1] - arrival
        frontier.append(VariableBatchPoint(payloads, completions, turnaround, cost))
    return VariableBatchSearch(
        digest,
        "feasible" if frontier else "infeasible",
        tuple(frontier),
        None,
    )


MAX_FIFO_BATCH_REQUESTS = 12


@dataclass(frozen=True)
class FifoBatchPoint(VariableBatchPoint):
    """Associate each timed run with its explicit FIFO request identities."""

    case_ids_by_run: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class FifoBatchSearch:
    """Describe a finite FIFO partition search with explicit idle accounting."""

    input_sha256: str
    state: Literal["feasible", "infeasible", "no_demand"]
    frontier: tuple[FifoBatchPoint, ...]
    idle_cost: StaticBatchCost | None


def _fifo_run(
    arrivals: tuple[tuple[Decimal, str], ...],
    ready: Decimal,
    policy: DynamicBatchPolicy,
) -> tuple[ScheduledRun, Decimal] | None:
    with localcontext() as arithmetic:
        arithmetic.prec = 50
        arithmetic.traps[Inexact] = True
        start = earliest_batch_start(max(ready, arrivals[-1][0]), policy)
        if start is None:
            return None
        complete = start + policy.run_duration_seconds
        turnaround = complete - arrivals[0][0]
        if turnaround > policy.turnaround_limit_seconds:
            return None
        return (
            ScheduledRun(
                start,
                complete,
                tuple(case for _, case in arrivals),
                policy.batch.controls_per_run,
            ),
            turnaround,
        )


def _fifo_plans(
    arrivals: tuple[tuple[Decimal, str], ...],
    policy: DynamicBatchPolicy,
) -> list[tuple[tuple[ScheduledRun, ...], Decimal]]:
    states: list[tuple[int, tuple[ScheduledRun, ...], Decimal]] = [
        (0, (), Decimal(0)),
    ]
    plans: list[tuple[tuple[ScheduledRun, ...], Decimal]] = []
    while states:
        served, runs, worst = states.pop()
        if served == len(arrivals):
            plans.append((runs, worst))
            continue
        if len(runs) >= policy.batch.max_runs:
            continue
        ready = runs[-1].complete_seconds if runs else Decimal(0)
        limit = min(policy.batch.payload_limit, len(arrivals) - served)
        for load in range(1, limit + 1):
            result = _fifo_run(arrivals[served : served + load], ready, policy)
            if result is not None:
                run, turnaround = result
                states.append((served + load, (*runs, run), max(worst, turnaround)))
    return plans


def enumerate_fifo_batch_plans(
    workload: Workload,
    policy: DynamicBatchPolicy,
    pricing: BatchPricing,
    context: ComputeCostContext,
) -> FifoBatchSearch:
    """Enumerate contiguous FIFO partitions with earliest feasible starts.

    The bounded domain permits known asynchronous arrivals on one resource,
    fixed duration, calendar and request turnaround constraints. Each selected
    run waits for all its assigned requests to arrive. Equal cost/TAT outcomes
    use the lexicographically first payload sequence as their representative.
    """
    workload = Workload.model_validate(workload.model_dump())
    policy = DynamicBatchPolicy.model_validate(policy.model_dump())
    pricing = BatchPricing.model_validate(pricing.model_dump())
    demand = validate_batch_demand(workload, policy.batch)
    if demand > MAX_FIFO_BATCH_REQUESTS:
        msg = "FIFO partition search demand exceeds its supported bound"
        raise ValueError(msg)
    if policy.max_wait_seconds != 0:
        msg = "FIFO partition search requires zero max wait"
        raise ValueError(msg)
    if any(w.end_seconds > workload.horizon_seconds for w in policy.windows):
        msg = "Availability window exceeds workload horizon"
        raise ValueError(msg)
    arrivals: list[tuple[Decimal, str]] = []
    for case in workload.cases:
        if case.arrival_seconds is None:
            msg = "FIFO partition search requires known arrivals"
            raise ValueError(msg)
        arrivals.append((case.arrival_seconds, case.case_id))
    ordered = tuple(sorted(arrivals))
    rates = _verified_rates(policy.batch, pricing, context)
    identity = {
        "format_version": "fifo-batch-search-v1",
        "workload": workload.model_dump(mode="json"),
        "policy": policy.model_dump(mode="json"),
        "pricing": pricing.model_dump(mode="json"),
        "ledger": context.ledger.model_dump(mode="json"),
        "validity": [v.model_dump(mode="json") for v in context.validity],
        "costing_date": context.costing_date.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    if demand == 0:
        idle = _assemble_cost(
            _CostDrivers(workload, policy.batch, pricing, context, (), digest),
            rates,
        )
        return FifoBatchSearch(digest, "no_demand", (), idle)
    points: list[FifoBatchPoint] = []
    for runs, worst in _fifo_plans(ordered, policy):
        payloads = tuple(len(run.case_ids) for run in runs)
        cost = _assemble_cost(
            _CostDrivers(
                workload,
                policy.batch,
                pricing,
                context,
                payloads,
                digest,
                "complete_modeled_workload",
            ),
            rates,
        )
        points.append(
            FifoBatchPoint(
                payloads,
                tuple(run.complete_seconds for run in runs),
                worst,
                cost,
                tuple(run.case_ids for run in runs),
            ),
        )
    points.sort(
        key=lambda p: (
            p.worst_turnaround_seconds,
            p.cost.total_cost,
            p.payloads,
        ),
    )
    frontier: list[FifoBatchPoint] = []
    for point in points:
        if not frontier or point.cost.total_cost < frontier[-1].cost.total_cost:
            frontier.append(point)
    return FifoBatchSearch(
        digest,
        "feasible" if frontier else "infeasible",
        tuple(frontier),
        None,
    )
